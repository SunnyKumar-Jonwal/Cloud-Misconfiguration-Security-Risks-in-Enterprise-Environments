#!/usr/bin/env python3
"""Compare CloudGuard with Checkov on the same Terraform (Chapter 6).

For every CloudGuard finding on the vulnerable estate, look up the Checkov
check(s) that test the same issue and report whether Checkov flagged it,
evaluated it and let it pass, or did not evaluate it at all. Also counts
what each tool reports on every example estate.

Checkov is run as an external program and is not a dependency of this
project. Install it separately (for example in its own virtual
environment) and pass its path:

    python tools/compare_with_checkov.py --checkov /path/to/venv/bin/checkov
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cloudguard.attack_paths import find_paths  # noqa: E402
from cloudguard.engine import load_rules, scan  # noqa: E402
from cloudguard.loader import load  # noqa: E402

# CloudGuard rule -> Checkov checks that test the same issue. The Checkov
# finding may be reported on a related resource (e.g. the bucket rather than
# its ACL resource), so matching is by issue, not by resource address.
EQUIVALENT = {
    "CG-S3-001": ["CKV_AWS_20"], "CG-S3-002": ["CKV2_AWS_6"], "CG-S3-003": ["CKV_AWS_54", "CKV_AWS_53", "CKV_AWS_55", "CKV_AWS_56"],
    "CG-S3-004": ["CKV_AWS_70"], "CG-S3-005": ["CKV_AWS_145", "CKV_AWS_19"], "CG-S3-006": ["CKV_AWS_21"],
    "CG-AZ-ST-001": ["CKV_AZURE_34"], "CG-AZ-ST-002": ["CKV_AZURE_190", "CKV2_AZURE_47", "CKV_AZURE_59"],
    "CG-AZ-ST-003": ["CKV_AZURE_44"], "CG-AZ-ST-004": ["CKV_AZURE_3"],
    "CG-IAM-001": ["CKV_AWS_62", "CKV_AWS_63"], "CG-IAM-002": ["CKV_AWS_288", "CKV_AWS_355"],
    "CG-IAM-003": [], "CG-IAM-004": ["CKV_AWS_274"], "CG-IAM-005": ["CKV_AWS_60"],
    "CG-NET-001": ["CKV_AWS_24", "CKV_AWS_25"], "CG-NET-002": ["CKV_AWS_277"],
    "CG-NET-003": ["CKV_AWS_277"], "CG-AZ-NET-001": ["CKV_AZURE_9", "CKV_AZURE_10"],
    "CG-EC2-001": ["CKV_AWS_79"], "CG-EC2-002": ["CKV_AWS_88"], "CG-EC2-003": ["CKV_AWS_46"],
    "CG-LAMBDA-001": ["CKV_AWS_45"], "CG-EBS-001": ["CKV_AWS_3"],
    "CG-RDS-001": ["CKV_AWS_17"], "CG-RDS-002": ["CKV_AWS_16"], "CG-RDS-003": ["CKV_AWS_133"], "CG-KMS-001": ["CKV_AWS_7"],
    "CG-AZ-SQL-001": ["CKV_AZURE_11"], "CG-AZ-SQL-002": ["CKV_AZURE_113"], "CG-AZ-KV-001": ["CKV_AZURE_110"],
    "CG-LOG-002": ["CKV_AWS_67"], "CG-LOG-003": ["CKV_AWS_36"], "CG-LOG-004": ["CKV_AWS_251"],
    "CG-VPC-001": ["CKV2_AWS_11"], "CG-EKS-001": ["CKV_AWS_38", "CKV_AWS_39"],
    "CG-AKS-001": ["CKV_AZURE_6", "CKV_AZURE_115"], "CG-AKS-002": ["CKV_AZURE_5"],
}
RELATED = {"CG-IAM-003": ["CKV_AWS_273"]}  # IAM users instead of SSO: related, not the same issue


def run_checkov(checkov: str, directory: Path) -> tuple[dict, float]:
    start = time.perf_counter()
    result = subprocess.run([checkov, "-d", str(directory), "--framework", "terraform", "-o", "json", "--compact"],
                            capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    data = json.loads(result.stdout)
    data = data[0] if isinstance(data, list) else data
    return data, elapsed


def statuses(data: dict) -> dict[tuple[str, str], str]:
    out = {}
    for kind in ("passed_checks", "failed_checks"):
        for c in data["results"].get(kind, []):
            out[(c["check_id"], c["resource"])] = "failed" if kind == "failed_checks" else "passed"
    return out


def related_addresses(address: str, inventory) -> set[str]:
    """The resource itself plus resources it references (e.g. ACL -> bucket)."""
    found = {address}
    resource = inventory.by_address.get(address)
    if resource:
        for value in resource.values.values():
            target = inventory.resolve(value)
            if target:
                found.add(target.address)
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkov", default="checkov", help="path to the checkov executable")
    parser.add_argument("--out", default=str(ROOT / "evaluation" / "checkov-comparison.md"))
    args = parser.parse_args(argv)

    rules = load_rules()
    rows = []
    totals = []
    for name, directory in [("vulnerable", ROOT / "examples/acme-retail/vulnerable"),
                            ("hardened", ROOT / "examples/acme-retail/hardened"),
                            ("drifted", ROOT / "examples/acme-retail/drifted"),
                            ("capital-one-replay", ROOT / "examples/capital-one-replay")]:
        start = time.perf_counter()
        inventory = load(directory)
        findings = scan(inventory, rules)
        cg_time = time.perf_counter() - start  # parsing + rule evaluation
        paths = find_paths(inventory)
        data, ck_time = run_checkov(args.checkov, directory)
        summary = data["summary"]
        totals.append((name, len(inventory), len(findings), len(paths), summary["failed"], summary["passed"],
                       cg_time, ck_time))
        if name != "vulnerable":
            continue
        status = statuses(data)
        for f in findings:
            addrs = related_addresses(f.address, inventory)
            outcome, evidence = "not evaluated", ""
            for check in EQUIVALENT.get(f.rule.id, []):
                hits = {status[(check, a)] for a in addrs if (check, a) in status}
                if "failed" in hits:
                    outcome, evidence = "detected", check
                    break
                if "passed" in hits and outcome == "not evaluated":
                    outcome, evidence = "missed (check passed)", check
            if outcome == "not evaluated" and f.rule.id in RELATED:
                for check in RELATED[f.rule.id]:
                    if any(status.get((check, a)) == "failed" for a in addrs | {"aws_iam_user.ci_deployer"}):
                        outcome, evidence = "related check only", check
            rows.append((f.rule.severity, f.rule.id, f.address, outcome, evidence))

    detected = sum(1 for r in rows if r[3] == "detected")
    lines = [
        "# CloudGuard and Checkov on the Same Terraform",
        "",
        "Generated by `tools/compare_with_checkov.py`. Checkov version: "
        f"{data['summary'].get('checkov_version', 'unknown')}.",
        "",
        "## Totals per estate",
        "",
        "| Estate | Resources | CloudGuard findings | CloudGuard attack paths | Checkov failed checks | Checkov passed checks |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, res, cg, ap, ck_f, ck_p, _, _ in totals:
        lines.append(f"| {name} | {res} | {cg} | {ap} | {ck_f} | {ck_p} |")
    lines += [
        "",
        f"## CloudGuard findings on the vulnerable estate: did Checkov flag the same issue? ({detected} of {len(rows)} detected)",
        "",
        "| Severity | CloudGuard rule | Resource | Checkov outcome | Checkov check |",
        "| --- | --- | --- | --- | --- |",
    ]
    for sev, rule, address, outcome, evidence in rows:
        lines.append(f"| {sev} | {rule} | `{address}` | {outcome} | {evidence or '-'} |")
    lines += ["", "## Scan time (seconds, single run, this machine)", "",
              "Indicative only: Checkov's time includes interpreter start-up and loading its full check library, and in",
              "the environment used it also tried to reach its vendor's API, which the network blocked.", "", "| Estate | CloudGuard (parse and scan, in process) | Checkov (whole run, separate process) |",
              "| --- | ---: | ---: |"]
    for name, *_, cg_time, ck_time in totals:
        lines.append(f"| {name} | {cg_time:.3f} | {ck_time:.2f} |")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
