"""Command-line interface.

    python -m cloudguard scan PATH [--format table|json|sarif|html] [--output FILE]
                                   [--fail-on critical|high|medium|low|none] [--min-severity LEVEL]
    python -m cloudguard rules

``scan`` exits with status 1 when a finding at or above ``--fail-on``
(default: high) is present, so it can block a pull request in CI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import reporters
from .engine import SEVERITY_ORDER, load_rules, scan
from .loader import load

LEVELS = ["critical", "high", "medium", "low", "info"]


def cmd_scan(args) -> int:
    inventory = load(args.path)
    rules = load_rules()
    findings = scan(inventory, rules, args.min_severity)
    target = str(args.path)
    if args.format == "table":
        text = reporters.to_table(findings, len(inventory), target, colour=not args.output and reporters.colour_enabled())
    elif args.format == "json":
        text = reporters.to_json(findings, len(inventory), target)
    elif args.format == "sarif":
        text = reporters.to_sarif(findings, rules)
    else:
        text = reporters.to_html(findings, len(inventory), target)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.output} ({len(findings)} findings)")
    else:
        print(text)
    return 1 if reporters.exceeds(findings, args.fail_on) else 0


def cmd_rules(args) -> int:
    rules = sorted(load_rules(), key=lambda r: (-SEVERITY_ORDER[r.severity], r.id))
    for r in rules:
        print(f"{r.id:<14} {r.severity:<9} {r.category:<17} {r.title}")
    print(f"\n{len(rules)} rules")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cloudguard", description="Policy-as-code scanner for Terraform (AWS and Azure)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="scan a Terraform directory or file")
    p_scan.add_argument("path", type=Path)
    p_scan.add_argument("--format", choices=["table", "json", "sarif", "html"], default="table")
    p_scan.add_argument("--output", help="write the report to this file instead of the terminal")
    p_scan.add_argument("--fail-on", choices=LEVELS[:4] + ["none"], default="high",
                        help="exit with status 1 if a finding of this severity or higher exists (default: high)")
    p_scan.add_argument("--min-severity", choices=LEVELS, default="info", help="hide findings below this severity")
    p_scan.set_defaults(func=cmd_scan)

    p_rules = sub.add_parser("rules", help="list the built-in rules")
    p_rules.set_defaults(func=cmd_rules)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
