#!/usr/bin/env python3
"""Capture a screenshot for every step of the local setup guide.

Every step is performed for real: the repository is cloned into a fresh
directory, a new virtual environment is created, dependencies are installed
from PyPI and each command is run inside that clone. The output of each step
is captured as a terminal screenshot in docs/setup-screenshots/.

The clone URL shown in the screenshots uses the placeholder ``<username>``.
The actual clone is made from this local checkout, which contains the same
files, so no personal account name appears anywhere in the images.

    NODE_PATH=$(npm root -g) python tools/capture_setup_guide.py
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_screenshots import ansi_to_html, capture, colour_plain  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "setup-screenshots"
WORK = ROOT / "build" / "local-setup"
HOME = WORK / "home"
REPO = "Cloud-Misconfiguration-Security-Risks-in-Enterprise-Environments"
CLONE_URL = f"https://github.com/<username>/{REPO}.git"

# Each step: file name, window title, list of (shown command, real command, show venv prompt), output lines to keep.
# A "real command" of None means: run the shown command as it is.
STEPS = [
    ("01-check-prerequisites", "Step 1: Check the prerequisites", [
        ("python3 --version", None, False),
        ("git --version", None, False),
        ("soffice --version", None, False),
    ], 20),
    ("02-clone-repository", "Step 2: Clone the repository", [
        (f"git clone {CLONE_URL}", f"git clone --quiet {ROOT} {REPO} && echo \"Cloning into '{REPO}'...\" && echo done.", False),
    ], 20),
    ("03-open-project-folder", "Step 3: Open the project folder", [
        (f"cd {REPO}", None, False),
        ("ls", "ls --color=always", False),
    ], 30),
    ("04-create-virtual-environment", "Step 4: Create and activate a virtual environment", [
        ("python3 -m venv .venv", None, False),
        ("source .venv/bin/activate", None, False),
        ("python --version", None, True),
    ], 20),
    ("05-install-dependencies", "Step 5: Install the dependencies", [
        ("pip install -r requirements.txt pytest", "pip install --disable-pip-version-check -r requirements.txt pytest", True),
    ], -8),
    ("06-run-tests", "Step 6: Run the test suite", [
        ("python -m pytest -q", None, True),
    ], 20),
    ("07-scan-the-vulnerable-estate", "Step 7: Scan the vulnerable example estate", [
        ("python -m cloudguard scan examples/acme-retail/vulnerable --min-severity critical", None, True),
    ], 60),
    ("08-scan-the-hardened-estate", "Step 8: Scan the hardened estate (should be clean)", [
        ("python -m cloudguard scan examples/acme-retail/hardened --fail-on low", None, True),
    ], 20),
    ("09-find-attack-paths", "Step 9: Find attack paths in the Capital One replay", [
        ("python -m cloudguard paths examples/capital-one-replay", None, True),
    ], 30),
    ("10-detect-drift", "Step 10: Detect drift against the approved baseline", [
        ("python -m cloudguard drift examples/acme-retail/hardened examples/acme-retail/drifted", None, True),
    ], 40),
    ("11-create-html-and-sarif-reports", "Step 11: Create the HTML and SARIF reports", [
        ("python -m cloudguard scan examples/acme-retail/vulnerable --format html --output build/report.html --fail-on none",
         None, True),
        ("python -m cloudguard scan examples/acme-retail/vulnerable --format sarif --output build/cloudguard.sarif --fail-on none",
         None, True),
    ], 20),
    ("13-build-the-report", "Step 13: Build the project report as DOCX and PDF", [
        ("python tools/build_report.py --pdf", None, True),
        ("du -h build/report.docx build/report.pdf", None, True),
    ], 20),
]

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


def prompt(cwd: Path, venv: bool) -> str:
    path = "~" if cwd == HOME else "~/" + str(cwd.relative_to(HOME))
    prefix = "<span class='venv'>(.venv) </span>" if venv else ""
    return f"{prefix}<span class='prompt'>user@laptop:{html.escape(path)}$ </span>"


def main() -> int:
    shutil.rmtree(WORK, ignore_errors=True)
    HOME.mkdir(parents=True)
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HOME=str(HOME), FORCE_COLOR="1", PY_COLORS="1", COLUMNS="110",
               PIP_PROGRESS_BAR="off", NODE_PATH=os.environ.get("NODE_PATH", ""))
    cwd = HOME
    clone = HOME / REPO

    for name, title, commands, keep in STEPS:
        parts = []
        for shown, real, venv in commands:
            real = real or shown
            if shown.startswith("cd "):
                cwd = HOME / shown[3:]
                parts.append(prompt(HOME, False) + f"<span class='cmd'>{html.escape(shown)}</span>")
                continue
            script = f"source {clone}/.venv/bin/activate && {real}" if venv else real
            result = subprocess.run(["bash", "-c", script], cwd=cwd, env=env, capture_output=True, text=True)
            output = (result.stdout + result.stderr).rstrip()
            lines = output.splitlines()
            if keep > 0 and len(lines) > keep:
                lines = lines[:keep] + [f"... ({len(output.splitlines()) - keep} more lines)"]
            elif keep < 0 and len(lines) > -keep:
                lines = [f"... ({len(lines) + keep} earlier lines)"] + lines[keep:]
            text = "\n".join(lines)
            body = ansi_to_html(text) if "\x1b[" in text else colour_plain(text)
            shown_prompt = prompt(cwd, venv or shown.startswith("python --version"))
            parts.append(shown_prompt + f"<span class='cmd'>{html.escape(shown)}</span>" + ("\n" + body if text else ""))
            if result.returncode not in (0, 1):
                print(f"warning: '{shown}' exited with {result.returncode}", file=sys.stderr)
        page = WORK / f"{name}.html"
        page.write_text(PAGE.format(title=html.escape(title), body="\n".join(parts)), encoding="utf-8")
        capture(page, OUT / f"{name}.png")
        print(f"captured {name}.png")

    # Step 12: the HTML report as it looks in a browser, created inside the fresh clone.
    capture(clone / "build" / "report.html", OUT / "12-open-html-report-in-browser.png", width=1280, max_height=760)
    print("captured 12-open-html-report-in-browser.png")

    # Step 14: first page of the PDF built inside the fresh clone.
    subprocess.run(["pdftoppm", "-png", "-r", "70", "-f", "1", "-l", "1", "-singlefile",
                    str(clone / "build" / "report.pdf"), str(OUT / "14-open-the-built-report")], check=True)
    print("captured 14-open-the-built-report.png")

    # Every GitHub URL shown must use the placeholder account (HTML-escaped in the pages).
    leaked = [p.name for p in WORK.glob("*.html")
              if re.search(r"github\.com/(?!&lt;username&gt;/)", p.read_text(encoding="utf-8"))]
    if leaked:
        print(f"error: a real GitHub URL appears in {leaked}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
