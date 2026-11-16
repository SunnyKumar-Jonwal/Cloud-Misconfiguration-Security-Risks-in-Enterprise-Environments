#!/usr/bin/env python3
"""Run CloudGuard's real commands and capture their output as screenshots.

Each command is executed for real in the repository; its coloured terminal
output is converted to HTML, shown in a terminal-style frame and captured
with headless Chromium (through tools/screenshot.js, which needs Node.js
with Playwright). The HTML scan report is captured as well.

    NODE_PATH=$(npm root -g) python tools/capture_screenshots.py

The Checkov comparison screenshot needs Checkov installed separately and
linked (or installed) at build/checkov-venv/bin/checkov; it is skipped if
that file does not exist.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
WORK = ROOT / "build" / "screens"
PROMPT = "user@hcl-lab:~/cloud-misconfiguration$ "

# (file name, command shown and run, max lines to keep; a negative number keeps the last lines)
COMMANDS = [
    ("01-pytest", "python -m pytest -q", 20),
    ("02-scan-vulnerable", "python -m cloudguard scan examples/acme-retail/vulnerable", 120),
    ("03-scan-hardened", "python -m cloudguard scan examples/acme-retail/hardened --fail-on low", 20),
    ("04-attack-paths-vulnerable", "python -m cloudguard paths examples/acme-retail/vulnerable", 60),
    ("05-attack-path-capital-one", "python -m cloudguard paths examples/capital-one-replay", 30),
    ("06-drift", "python -m cloudguard drift examples/acme-retail/hardened examples/acme-retail/drifted", 40),
    ("07-rules", "python -m cloudguard rules", 60),
    ("08-sarif-output",
     "python -m cloudguard scan examples/acme-retail/vulnerable --format sarif --output build/cloudguard.sarif "
     "--fail-on none && python -c \"import json; r=json.load(open('build/cloudguard.sarif'))['runs'][0]; "
     "print(len(r['results']), 'results,', len(r['tool']['driver']['rules']), 'rules'); "
     "print(json.dumps(r['results'][0], indent=2))\"", 40),
    ("09-checkov-comparison",
     "python tools/compare_with_checkov.py --checkov build/checkov-venv/bin/checkov --out build/checkov-comparison.md "
     "| grep -E '^## |^. (Estate|vulnerable . 41|hardened . 46|drifted . 46|capital-one-replay . 9) |missed|related'", 40),
]

ANSI_RE = re.compile(r"\x1b\[([\d;]*)m")
ANSI_STYLE = {"1": "font-weight:700", "31": "color:#ff6b6b", "32": "color:#5fd38d", "33": "color:#ffd166",
              "34": "color:#6ea8fe", "35": "color:#d291ff", "36": "color:#4fd1e8", "37": "color:#e6e9ef",
              "90": "color:#8b93a6"}
DECISION_STYLE = [(re.compile(r"\b(passed|detected)\b"), "#5fd38d"), (re.compile(r"\b(failed|missed)\b"), "#ff6b6b")]

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
body {{ margin:0; background:#e9ecf1; padding:18px; font-family: "Liberation Mono", Consolas, monospace; }}
.win {{ background:#1e2230; border-radius:10px; box-shadow:0 6px 24px rgba(0,0,0,.25); overflow:hidden; }}
.bar {{ background:#2b3042; padding:9px 12px; display:flex; gap:7px; align-items:center; }}
.dot {{ width:12px; height:12px; border-radius:50%; display:inline-block; }}
.title {{ color:#e6e9ef; font-size:13px; margin-left:10px; font-weight:700; font-family: "Liberation Sans", Arial, sans-serif; }}
pre {{ margin:0; padding:14px 16px 18px; color:#e6e9ef; font-size:13px; line-height:1.45; white-space:pre-wrap; word-break:break-word; }}
.prompt {{ color:#5fd38d; }} .venv {{ color:#8b93a6; }} .cmd {{ color:#ffffff; font-weight:700; }}
</style></head><body><div class="win"><div class="bar">
<span class="dot" style="background:#ff5f56"></span><span class="dot" style="background:#ffbd2e"></span>
<span class="dot" style="background:#27c93f"></span><span class="title">{title}</span></div>
<pre>{body}</pre></div></body></html>"""


def ansi_to_html(text: str) -> str:
    out, open_spans, pos = [], 0, 0
    for m in ANSI_RE.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        pos = m.end()
        codes = [c for c in m.group(1).split(";") if c]
        if not codes or codes == ["0"]:
            out.append("</span>" * open_spans)
            open_spans = 0
        else:
            style = ";".join(ANSI_STYLE[c] for c in codes if c in ANSI_STYLE)
            out.append(f"<span style='{style}'>")
            open_spans += 1
    out.append(html.escape(text[pos:]))
    out.append("</span>" * open_spans)
    return "".join(out)


def colour_plain(text: str) -> str:
    """Colour key words in output that has no ANSI codes of its own."""
    body = html.escape(text)
    for pattern, colour in DECISION_STYLE:
        body = pattern.sub(lambda m, c=colour: f"<span style='color:{c};font-weight:700'>{m.group(0)}</span>", body)
    return body


def run(command: str, cwd: Path = ROOT, extra_env: dict | None = None) -> tuple[str, int]:
    env = dict(os.environ, PYTHONPATH=str(ROOT), COLUMNS="110", FORCE_COLOR="1", PY_COLORS="1", **(extra_env or {}))
    command = re.sub(r"^python ", f"{sys.executable} ", command)
    command = command.replace("&& python ", f"&& {sys.executable} ")
    result = subprocess.run(["bash", "-c", command], cwd=cwd, env=env, capture_output=True, text=True)
    return (result.stdout + result.stderr).rstrip(), result.returncode


def trim(output: str, keep: int) -> str:
    lines = output.splitlines()
    if keep > 0 and len(lines) > keep:
        lines = lines[:keep] + [f"... ({len(output.splitlines()) - keep} more lines)"]
    elif keep < 0 and len(lines) > -keep:
        lines = [f"... ({len(lines) + keep} earlier lines)"] + lines[keep:]
    return "\n".join(lines)


def to_body(text: str) -> str:
    return ansi_to_html(text) if "\x1b[" in text else colour_plain(text)


def capture(page: Path, png: Path, width: int = 1100, max_height: int = 0, selector: str | None = None):
    argv = ["node", str(ROOT / "tools" / "screenshot.js"), str(page), str(png), str(width), str(max_height)]
    if selector:
        argv.append(selector)
    subprocess.run(argv, check=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    for name, command, keep in COMMANDS:
        if "checkov-venv" in command and not (ROOT / "build/checkov-venv/bin/checkov").exists():
            print(f"skipped {name} (Checkov not installed at build/checkov-venv)")
            continue
        output, _ = run(command)
        shown = command
        body = (f"<span class='prompt'>{html.escape(PROMPT)}</span><span class='cmd'>{html.escape(shown)}</span>\n"
                + to_body(trim(output, keep)))
        page = WORK / f"{name}.html"
        page.write_text(PAGE.format(title=html.escape(name), body=body), encoding="utf-8")
        capture(page, OUT / f"{name}.png")
        print(f"captured {name}.png")

    report = ROOT / "build" / "cloudguard-report.html"
    run(f"python -m cloudguard scan examples/acme-retail/vulnerable --format html --output {report} --fail-on none")
    capture(report, OUT / "10-html-report-summary.png", width=1280, max_height=900)
    print("captured 10-html-report-summary.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
