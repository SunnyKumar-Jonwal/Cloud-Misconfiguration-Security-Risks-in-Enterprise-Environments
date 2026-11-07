#!/usr/bin/env python3
"""Structural checks for the report sources in ``report/``.

Checks that run on every branch:

* every source file starts with exactly one ``# Title``
* section, table and figure numbers match the chapter file (``03-*.md`` must
  use ``## 3.1``, ``Table 3.1`` …) and run without gaps
* figure files exist and ``{{placeholders}}`` resolve against metadata.yaml
* every ``[n]`` citation has an entry in ``references.md``
* no leftover ``TODO``/``TBD``/``FIXME``/lorem ipsum markers

With ``--strict`` (used for release branches and ``main``) the report must
also be complete: all preliminary pages listed in metadata.yaml, chapters
numbered 01..N without gaps and at least seven of them, and a reference list
in which every entry is cited somewhere.

Problems are printed as GitHub Actions annotations so they show up on the
pull request diff.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
MIN_CHAPTERS = 7

CITATION_RE = re.compile(r"(?<![!\w])\[(\d+(?:\s*[,–-]\s*\d+)*)\](?!\()")
REFERENCE_RE = re.compile(r"^\[(\d+)\]\s+\S")
FORBIDDEN_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b|lorem ipsum", re.I)
PLACEHOLDER_RE = re.compile(r"\{\{(.*?)\}\}")
SECTION_RE = re.compile(r"^(#{2,3})\s+(\d+(?:\.\d+)+)\s+\S")
CAPTION_RE = re.compile(r"^(?:!\[)?(Table|Figure)\s+(\d+)\.(\d+):")
IMAGE_RE = re.compile(r"^!\[.*?\]\((.*?)\)")


class Checker:
    def __init__(self, strict: bool):
        self.strict = strict
        self.errors = 0
        self.warnings = 0

    def error(self, path: Path, line: int, message: str):
        self.errors += 1
        print(f"::error file={path.relative_to(ROOT)},line={line}::{message}")

    def warn(self, path: Path, line: int, message: str):
        self.warnings += 1
        print(f"::warning file={path.relative_to(ROOT)},line={line}::{message}")

    def problem(self, path: Path, line: int, message: str):
        """An error in strict mode, a warning otherwise."""
        (self.error if self.strict else self.warn)(path, line, message)


def prose_lines(path: Path):
    """Yield (line number, text) for lines outside fenced code blocks."""
    in_code = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            yield number, line


def expand_citation(group: str) -> list[int]:
    numbers: list[int] = []
    for part in re.split(r"\s*,\s*", group):
        if re.search(r"[–-]", part):
            low, high = (int(x) for x in re.split(r"\s*[–-]\s*", part))
            numbers.extend(range(low, high + 1))
        else:
            numbers.append(int(part))
    return numbers


def resolve(meta: dict, key: str) -> bool:
    value = meta
    for part in key.strip().split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return True


def check_file(path: Path, chk: Checker, meta: dict, chapter: int | None, cited: dict[int, tuple[Path, int]]):
    h1_count = 0
    first_heading_seen = False
    section = subsection = 0
    counters = {"Table": 0, "Figure": 0}

    for number, line in prose_lines(path):
        stripped = line.strip()

        if stripped.startswith("# "):
            h1_count += 1
            if h1_count > 1:
                chk.error(path, number, "more than one top-level '# ' heading in this file")
        if stripped.startswith("#") and not first_heading_seen:
            first_heading_seen = True
            if not stripped.startswith("# "):
                chk.error(path, number, "file must start with a '# Title' heading")

        if FORBIDDEN_RE.search(stripped):
            chk.error(path, number, f"leftover marker: {FORBIDDEN_RE.search(stripped).group(0)!r}")

        for match in PLACEHOLDER_RE.finditer(stripped):
            if not resolve(meta, match.group(1)):
                chk.error(path, number, f"placeholder {{{{{match.group(1)}}}}} is not defined in metadata.yaml")

        image = IMAGE_RE.match(stripped)
        if image and not (REPORT / image.group(1)).exists():
            chk.error(path, number, f"figure file not found: {image.group(1)}")

        if path.name != "references.md":
            for match in CITATION_RE.finditer(stripped):
                for ref in expand_citation(match.group(1)):
                    cited.setdefault(ref, (path, number))

        if chapter is None:
            continue

        heading = SECTION_RE.match(stripped)
        if heading:
            level, parts = len(heading.group(1)), [int(p) for p in heading.group(2).split(".")]
            if parts[0] != chapter:
                chk.error(path, number, f"section {heading.group(2)} is in chapter {chapter}")
            elif level == 2:
                if len(parts) != 2 or parts[1] != section + 1:
                    chk.error(path, number, f"expected section {chapter}.{section + 1}, found {heading.group(2)}")
                section, subsection = parts[1] if len(parts) > 1 else section, 0
            elif level == 3:
                if len(parts) != 3 or parts[1] != section or parts[2] != subsection + 1:
                    chk.error(
                        path, number, f"expected subsection {chapter}.{section}.{subsection + 1}, found {heading.group(2)}"
                    )
                subsection = parts[2] if len(parts) > 2 else subsection
        elif re.match(r"^#{2,3}\s+", stripped):
            chk.error(path, number, "chapter sections must be numbered, e.g. '## 3.1 Title'")

        caption = CAPTION_RE.match(stripped)
        if caption:
            kind, chap, index = caption.group(1), int(caption.group(2)), int(caption.group(3))
            expected = counters[kind] + 1
            if chap != chapter or index != expected:
                chk.error(path, number, f"expected {kind} {chapter}.{expected}, found {kind} {chap}.{index}")
            counters[kind] = index

    if h1_count == 0:
        chk.error(path, 1, "file has no '# Title' heading")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the report sources.")
    parser.add_argument("--strict", action="store_true", help="also require a complete report")
    args = parser.parse_args(argv)
    chk = Checker(args.strict)

    meta_path = REPORT / "metadata.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    for key in ("title", "student", "guide", "institute", "organisation", "front_matter"):
        if key not in meta:
            chk.error(meta_path, 1, f"metadata.yaml is missing '{key}'")

    cited: dict[int, tuple[Path, int]] = {}

    for name in meta.get("front_matter", []):
        if name == "@toc":
            continue
        path = REPORT / "front-matter" / name
        if path.exists():
            check_file(path, chk, meta, None, cited)
        else:
            chk.problem(meta_path, 1, f"preliminary page front-matter/{name} does not exist yet")

    chapters = sorted((REPORT / "chapters").glob("*.md"))
    numbers = []
    for path in chapters:
        match = re.match(r"^(\d{2})-[a-z0-9-]+\.md$", path.name)
        if not match:
            chk.error(path, 1, "chapter files must be named NN-short-name.md")
            continue
        numbers.append(int(match.group(1)))
        check_file(path, chk, meta, int(match.group(1)), cited)

    if numbers != list(range(1, len(numbers) + 1)):
        chk.problem(REPORT / "chapters", 1, f"chapter files are not numbered 01..N without gaps: {numbers}")
    if len(numbers) < MIN_CHAPTERS:
        chk.problem(REPORT / "chapters", 1, f"report has {len(numbers)} chapters, expected at least {MIN_CHAPTERS}")

    for path in sorted((REPORT / "appendices").glob("*.md")):
        check_file(path, chk, meta, None, cited)

    refs_path = REPORT / "references.md"
    if refs_path.exists():
        check_file(refs_path, chk, meta, None, cited)
        entries = {}
        for number, line in prose_lines(refs_path):
            match = REFERENCE_RE.match(line.strip())
            if match:
                entries[int(match.group(1))] = number
        if list(entries) != list(range(1, len(entries) + 1)):
            chk.error(refs_path, 1, "reference entries must be numbered [1]..[N] in order")
        for ref, (path, line) in sorted(cited.items()):
            if ref not in entries:
                chk.error(path, line, f"citation [{ref}] has no entry in references.md")
        for ref, line in entries.items():
            if ref not in cited:
                chk.problem(refs_path, line, f"reference [{ref}] is never cited in the report")
    elif cited:
        chk.problem(REPORT, 1, f"{len(cited)} citations used but references.md does not exist yet")

    mode = "strict" if args.strict else "standard"
    print(f"report check ({mode}): {len(chapters)} chapters, {len(cited)} distinct citations, "
          f"{chk.errors} error(s), {chk.warnings} warning(s)")
    return 1 if chk.errors else 0


if __name__ == "__main__":
    sys.exit(main())
