#!/usr/bin/env python3
"""Generate Appendix B (the CloudGuard rule catalogue) from cloudguard/rules/*.yaml.

    python tools/generate_rule_catalogue.py          # rewrite the appendix
    python tools/generate_rule_catalogue.py --check  # fail if it is out of date
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cloudguard.engine import SEVERITY_ORDER, load_rules  # noqa: E402

OUT = ROOT / "report" / "appendices" / "b-cloudguard-rule-catalogue.md"
CATEGORY_NAMES = {
    "storage-exposure": "Storage exposure", "identity": "Identity and access", "network-exposure": "Network exposure",
    "compute": "Compute and metadata", "secrets": "Secrets", "data-protection": "Data protection",
    "logging": "Logging and monitoring", "resilience": "Resilience",
}


def render() -> str:
    rules = load_rules()
    lines = [
        "# Appendix B: CloudGuard Rule Catalogue",
        "",
        "This appendix lists every rule in CloudGuard's rule set. It is generated from the YAML files in "
        "`cloudguard/rules/` by `tools/generate_rule_catalogue.py`, and a test fails if it falls out of date, "
        "so the report always matches the code. Each rule's remediation advice and example fix are in the "
        "rule file and in the scanner's HTML report.",
        "",
        f"The catalogue contains {len(rules)} rules: "
        + ", ".join(f"{sum(r.severity == s for r in rules)} {s}" for s in ("critical", "high", "medium", "low")) + ".",
    ]
    for category, title in CATEGORY_NAMES.items():
        group = sorted((r for r in rules if r.category == category), key=lambda r: (-SEVERITY_ORDER[r.severity], r.id))
        if not group:
            continue
        lines += ["", f"## {title}", "", "| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |", "| --- | --- | --- | --- | --- |"]
        for r in group:
            nist = ", ".join(r.frameworks.get("nist_800_53", [])) or "-"
            attack = ", ".join(r.frameworks.get("mitre_attack", [])) or "-"
            title_text = r.title.replace("|", "\\|")
            lines.append(f"| {r.id} | {r.severity} | {title_text} | {nist} | {attack} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.relative_to(ROOT)} is out of date; run python tools/generate_rule_catalogue.py")
            return 1
        print("rule catalogue is up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
