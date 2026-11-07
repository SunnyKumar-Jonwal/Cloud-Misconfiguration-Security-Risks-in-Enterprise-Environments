"""Configuration drift: compare an approved baseline with the current configuration.

Misconfigurations often appear after a review, through emergency changes,
console edits that are later imported, or "temporary" exceptions. This
module compares two Terraform directories and reports:

* resources added, removed and changed (with the attribute paths that changed)
* findings introduced since the baseline, and findings resolved
* which introduced findings are explained by which changed attributes
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .engine import Finding, Rule, scan
from .loader import Inventory


@dataclass
class ResourceChange:
    address: str
    changed_paths: list[str] = field(default_factory=list)


@dataclass
class DriftReport:
    added: list[str]
    removed: list[str]
    changed: list[ResourceChange]
    new_findings: list[Finding]
    resolved_findings: list[Finding]

    @property
    def has_security_drift(self) -> bool:
        return bool(self.new_findings)


def _diff(old, new, prefix: str = "") -> list[str]:
    """Attribute paths whose values differ between two nested structures."""
    if isinstance(old, dict) and isinstance(new, dict):
        paths = []
        for key in sorted(set(old) | set(new)):
            paths += _diff(old.get(key), new.get(key), f"{prefix}.{key}" if prefix else key)
        return paths
    if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        paths = []
        for i, (a, b) in enumerate(zip(old, new)):
            paths += _diff(a, b, f"{prefix}.{i}")
        return paths
    return [] if old == new else [prefix or "(value)"]


def compare(baseline: Inventory, current: Inventory, rules: list[Rule]) -> DriftReport:
    base_addresses, cur_addresses = set(baseline.by_address), set(current.by_address)
    changed = []
    for address in sorted(base_addresses & cur_addresses):
        paths = _diff(baseline.by_address[address].values, current.by_address[address].values)
        if paths:
            changed.append(ResourceChange(address, paths))

    def key(f: Finding) -> tuple[str, str]:
        return f.rule.id, f.address

    before = {key(f): f for f in scan(baseline, rules)}
    after = {key(f): f for f in scan(current, rules)}
    return DriftReport(
        added=sorted(cur_addresses - base_addresses),
        removed=sorted(base_addresses - cur_addresses),
        changed=changed,
        new_findings=[after[k] for k in after if k not in before],
        resolved_findings=[before[k] for k in before if k not in after],
    )


def explain(report: DriftReport) -> dict[str, list[str]]:
    """Map each new finding (rule id + address) to the changed attributes of its resource."""
    changes = {c.address: c.changed_paths for c in report.changed}
    return {f"{f.rule.id} {f.address}": changes.get(f.address, ["(new resource)"]) for f in report.new_findings}
