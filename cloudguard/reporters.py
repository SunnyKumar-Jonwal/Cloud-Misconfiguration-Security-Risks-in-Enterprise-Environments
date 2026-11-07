"""Output formats for scan results: table, JSON, SARIF 2.1.0 and HTML."""

from __future__ import annotations

import html
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .engine import SEVERITY_ORDER, Finding, Rule

SARIF_LEVEL = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}
SARIF_SCORE = {"critical": "9.5", "high": "8.0", "medium": "5.5", "low": "3.0", "info": "0.0"}
ANSI = {"critical": "1;31", "high": "31", "medium": "33", "low": "36", "info": "37", "bold": "1", "grey": "90",
        "green": "32"}


def colour_enabled(stream=sys.stdout) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(os.environ.get("FORCE_COLOR")) or stream.isatty()


def _relative(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path.cwd()))
    except ValueError:
        return path


def severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts = Counter(f.rule.severity for f in findings)
    return {s: counts.get(s, 0) for s in ("critical", "high", "medium", "low")}


def to_table(findings: list[Finding], resources: int, target: str, colour: bool = False) -> str:
    def paint(text, style):
        return f"\033[{ANSI[style]}m{text}\033[0m" if colour else text

    lines = [paint(f"CloudGuard scan of {target}: {resources} resources checked", "bold"), ""]
    if findings:
        lines.append(f"{'SEVERITY':<9} {'RULE':<14} {'RESOURCE':<48} LOCATION")
        for f in findings:
            location = f"{Path(f.file).name}:{f.line}"
            lines.append(f"{paint(f'{f.rule.severity.upper():<9}', f.rule.severity)} {f.rule.id:<14} "
                         f"{f.address:<48} {location}")
            lines.append(paint(f"{'':<25}{f.rule.title}", "grey"))
    else:
        lines.append(paint("No misconfigurations found.", "green"))
    counts = severity_counts(findings)
    summary = ", ".join(f"{paint(str(n), s) if n else n} {s}" for s, n in counts.items())
    lines += ["", f"{len(findings)} findings: {summary}"]
    return "\n".join(lines)


def to_json(findings: list[Finding], resources: int, target: str) -> str:
    return json.dumps({
        "target": target, "resources": resources, "summary": severity_counts(findings),
        "findings": [f.as_dict() | {"file": _relative(f.file)} for f in findings],
    }, indent=2)


def to_sarif(findings: list[Finding], rules: list[Rule]) -> str:
    used = {f.rule.id for f in findings}
    sarif_rules = []
    for r in rules:
        if r.id not in used:
            continue
        tags = ["security", r.category] + [f"NIST-{c}" for c in r.frameworks.get("nist_800_53", [])] \
            + [f"ATTACK-{t}" for t in r.frameworks.get("mitre_attack", [])]
        sarif_rules.append({
            "id": r.id,
            "name": r.title,
            "shortDescription": {"text": r.title},
            "fullDescription": {"text": r.description or r.title},
            "help": {"text": f"{r.remediation}\n\nExample fix:\n{r.fix}", "markdown": f"{r.remediation}\n\n```hcl\n{r.fix}```"},
            "defaultConfiguration": {"level": SARIF_LEVEL[r.severity]},
            "properties": {"security-severity": SARIF_SCORE[r.severity], "tags": tags},
        })
    results = [{
        "ruleId": f.rule.id,
        "level": SARIF_LEVEL[f.rule.severity],
        "message": {"text": f"{f.rule.title} ({f.address})"},
        "locations": [{"physicalLocation": {
            "artifactLocation": {"uri": _relative(f.file)},
            "region": {"startLine": f.line},
        }}],
    } for f in findings]
    return json.dumps({
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "CloudGuard", "version": "1.0.0", "rules": sarif_rules}},
                  "results": results}],
    }, indent=2)


CSS = """
:root{--bg:#f5f6f8;--card:#fff;--ink:#1d2433;--muted:#5d6678;--line:#e3e6ec;--critical:#9b1c1c;--high:#c2410c;
--medium:#a16207;--low:#0e7490;--ok:#15803d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 "Segoe UI","Liberation Sans",Arial,sans-serif}
header{background:#0f2942;color:#fff;padding:18px 28px}header h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:#c7d3e3;font-size:13px}
main{padding:22px 28px;max-width:1240px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.card .value{font-size:28px;font-weight:700;margin-top:4px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:22px}section h2{margin:0 0 12px;font-size:16px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;background:#fafbfc}.sev{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:700;color:#fff}
.critical{background:var(--critical)}.high{background:var(--high)}.medium{background:var(--medium)}.low{background:var(--low)}
.t-critical{color:var(--critical)}.t-high{color:var(--high)}.t-medium{color:var(--medium)}.t-low{color:var(--low)}.t-ok{color:var(--ok)}
code,pre{font-family:Consolas,"Liberation Mono",monospace;font-size:12px}pre{background:#f0f2f5;padding:6px 8px;border-radius:6px;margin:4px 0 0;white-space:pre-wrap}
.muted{color:var(--muted)}
"""


def to_html(findings: list[Finding], resources: int, target: str) -> str:
    counts = severity_counts(findings)
    categories = Counter(f.rule.category for f in findings)
    e = html.escape
    out = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>CloudGuard Scan Report</title><style>{CSS}</style></head><body>",
        f"<header><h1>CloudGuard: Cloud Misconfiguration Scan Report</h1><p>Target <code>{e(target)}</code> &middot; "
        f"{resources} resources checked &middot; generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}</p></header><main>",
        "<div class='cards'>",
        f"<div class='card'><div class='label'>Resources</div><div class='value'>{resources}</div></div>",
        f"<div class='card'><div class='label'>Findings</div><div class='value'>{len(findings)}</div></div>",
    ]
    for sev, n in counts.items():
        out.append(f"<div class='card'><div class='label'>{sev}</div><div class='value t-{sev}'>{n}</div></div>")
    out.append("</div>")
    if categories:
        out.append("<section><h2>Findings by category</h2><table><tr><th>Category</th><th>Findings</th></tr>")
        for cat, n in categories.most_common():
            out.append(f"<tr><td>{e(cat)}</td><td>{n}</td></tr>")
        out.append("</table></section>")
    out.append("<section><h2>Findings</h2>")
    if not findings:
        out.append("<p class='t-ok'><b>No misconfigurations found.</b></p>")
    else:
        out.append("<table><tr><th>Severity</th><th>Rule</th><th>Resource</th><th>Issue and remediation</th>"
                   "<th>Mappings</th></tr>")
        for f in findings:
            fw = f.rule.frameworks
            maps = ", ".join(fw.get("nist_800_53", []))
            attack = ", ".join(fw.get("mitre_attack", []))
            out.append(
                f"<tr><td><span class='sev {f.rule.severity}'>{e(f.rule.severity)}</span></td>"
                f"<td><code>{e(f.rule.id)}</code></td>"
                f"<td><code>{e(f.address)}</code><br><span class='muted'>{e(Path(f.file).name)}:{f.line}</span></td>"
                f"<td><b>{e(f.rule.title)}</b><br>{e(f.rule.remediation)}<pre>{e(f.rule.fix.strip())}</pre></td>"
                f"<td class='muted'>NIST {e(maps) or '-'}<br>ATT&amp;CK {e(attack) or '-'}</td></tr>")
        out.append("</table>")
    out.append("</section></main></body></html>")
    return "\n".join(out)


def exceeds(findings: list[Finding], fail_on: str) -> bool:
    return fail_on != "none" and any(f.rule.rank >= SEVERITY_ORDER[fail_on] for f in findings)
