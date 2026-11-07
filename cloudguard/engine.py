"""Policy-as-code rule engine.

Rules are YAML documents (see ``cloudguard/rules/``). Each rule names the
resource types it applies to and a ``when`` condition; a resource for which
the condition is true produces a finding. Conditions are built from:

Combinators
    ``all: [...]``, ``any: [...]``, ``not: {...}``, ``always: true``
Attribute tests (``path`` is dotted, list indexes are numbers, e.g.
``metadata_options.0.http_tokens``)
    ``equals``, ``not_equals``, ``in``, ``not_in``, ``exists``, ``truthy``,
    ``matches`` (regex), ``lt``, ``gt``
Lists
    ``any_item: {path, where}``: some item of the list satisfies ``where``
Network
    ``cidr_open: true`` (the value contains 0.0.0.0/0, ::/0, * or Internet),
    ``port_includes: [22, 3389]`` with ``from``/``to`` port paths
IAM policy documents
    ``statement: {path, where}`` where ``where`` may use ``effect``,
    ``action_is`` (literal value, e.g. "*"), ``action_covers`` (the policy's
    wildcards grant a concrete action), ``resource_in`` (literal value),
    ``principal_public`` and ``has_condition``
Relationships
    ``missing_related: {type, via}``: no resource of ``type`` points at this
    one through attribute ``via``
Secrets
    ``secret_in: path``: a hard-coded credential appears under ``path``

Inventory-wide rules (``resource_types: [__inventory__]``) use
``inventory_missing: [types...]`` and produce one finding for the estate.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .loader import Inventory, Resource

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
OPEN_CIDRS = {"0.0.0.0/0", "::/0", "*", "internet", "any"}
SECRET_VALUE_RE = re.compile(
    r"(AKIA|ASIA)[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{36,}|xox[abpors]-[A-Za-z0-9-]{10,}"
    r"|(?i:(password|passwd|pwd|secret|token|api[_-]?key)\s*[=:]\s*['\"]?[^\s'\"$]{6,})"
)
# ARNs such as arn:aws:secretsmanager:...:secret:app/db point to a secret store; they are
# the safe pattern, not a hard-coded secret, so they are removed before matching.
ARN_RE = re.compile(r"arn:aws[\w-]*:[^\s'\"]+")
SECRET_NAME_RE = re.compile(r"(?i)(password|passwd|pwd|secret|token|api[_-]?key|private[_-]?key)")
RULES_DIR = Path(__file__).parent / "rules"


@dataclass
class Rule:
    id: str
    title: str
    severity: str
    resource_types: list[str]
    category: str
    when: dict
    description: str = ""
    remediation: str = ""
    fix: str = ""
    frameworks: dict = field(default_factory=dict)

    @property
    def rank(self) -> int:
        return SEVERITY_ORDER[self.severity]


@dataclass
class Finding:
    rule: Rule
    address: str
    file: str
    line: int
    resource: Resource | None = None

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule.id, "title": self.rule.title, "severity": self.rule.severity,
            "category": self.rule.category, "resource": self.address, "file": self.file, "line": self.line,
            "remediation": self.rule.remediation, "frameworks": self.rule.frameworks,
        }


def load_rules(directory: Path = RULES_DIR) -> list[Rule]:
    rules = []
    for path in sorted(directory.glob("*.yaml")):
        for item in yaml.safe_load(path.read_text(encoding="utf-8")):
            rules.append(Rule(**item))
    ids = [r.id for r in rules]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate rule ids: {sorted(duplicates)}")
    for rule in rules:
        if rule.severity not in SEVERITY_ORDER:
            raise ValueError(f"{rule.id}: unknown severity {rule.severity!r}")
    return rules


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------

_MISSING = object()


def get_path(value, path: str):
    for part in str(path).split("."):
        if part == "":
            continue
        if isinstance(value, list):
            if part.isdigit() and int(part) < len(value):
                value = value[int(part)]
            else:
                return _MISSING
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return _MISSING
    return value


def as_list(value) -> list:
    if value is _MISSING or value is None:
        return []
    return value if isinstance(value, list) else [value]


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _strings(value):
    """Yield every (key, string) pair inside a nested structure."""
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, str):
                yield k, v
            else:
                yield from _strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield "", value


def has_secret(value) -> bool:
    for key, text in _strings(value):
        if text.startswith("${"):
            continue  # a reference to a variable or secret store, not a literal
        text = ARN_RE.sub("", text)
        if SECRET_VALUE_RE.search(text):
            return True
        if key and SECRET_NAME_RE.search(key) and len(text) >= 6:
            return True
    return False


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

def _literal_in(values, allowed) -> bool:
    allowed = {str(a).lower() for a in as_list(allowed)}
    return any(str(v).lower() in allowed for v in as_list(values))


def _covers(policy_actions, concrete_actions) -> bool:
    """True if any policy action pattern (which may use * and ?) grants a concrete action."""
    return any(
        fnmatch.fnmatchcase(str(action).lower(), str(pattern).lower())
        for pattern in as_list(policy_actions)
        for action in as_list(concrete_actions)
    )


def _principal_public(principal) -> bool:
    if principal == "*":
        return True
    if isinstance(principal, dict):
        return any(v == "*" or (isinstance(v, list) and "*" in v) for v in principal.values())
    return False


def _eval_statement(stmt: dict, cond: dict) -> bool:
    for key, expected in cond.items():
        if key == "effect":
            if str(stmt.get("Effect", "")).lower() != str(expected).lower():
                return False
        elif key == "action_is":
            # the policy literally grants one of these values, e.g. "*"
            if not _literal_in(stmt.get("Action"), expected):
                return False
        elif key == "action_covers":
            # the policy's (possibly wildcarded) actions grant one of these concrete actions
            if not _covers(stmt.get("Action"), expected):
                return False
        elif key == "resource_in":
            if not _literal_in(stmt.get("Resource"), expected):
                return False
        elif key == "principal_public":
            if _principal_public(stmt.get("Principal")) != bool(expected):
                return False
        elif key == "has_condition":
            if bool(stmt.get("Condition")) != bool(expected):
                return False
        else:
            raise ValueError(f"unknown statement test {key!r}")
    return True


def evaluate(cond: dict, root, resource: Resource | None, inventory: Inventory) -> bool:
    """Evaluate a condition against ``root`` (a resource's values or a list item)."""
    if "all" in cond:
        return all(evaluate(c, root, resource, inventory) for c in cond["all"])
    if "any" in cond:
        return any(evaluate(c, root, resource, inventory) for c in cond["any"])
    if "not" in cond:
        return not evaluate(cond["not"], root, resource, inventory)
    if "always" in cond:
        return bool(cond["always"])
    if "any_item" in cond:
        spec = cond["any_item"]
        return any(evaluate(spec["where"], item, resource, inventory) for item in as_list(get_path(root, spec["path"])))
    if "statement" in cond:
        spec = cond["statement"]
        document = get_path(root, spec["path"])
        if not isinstance(document, dict):
            return False
        return any(_eval_statement(s, spec["where"]) for s in as_list(document.get("Statement")) if isinstance(s, dict))
    if "missing_related" in cond:
        spec = cond["missing_related"]
        return not any(inventory.refers_to(r.values.get(spec["via"]), resource) for r in inventory.of_type(spec["type"]))
    if "secret_in" in cond:
        value = get_path(root, cond["secret_in"])
        return value is not _MISSING and has_secret(value)
    if "inventory_missing" in cond:
        return not inventory.of_type(*as_list(cond["inventory_missing"]))
    if "cidr_open" in cond:
        values = [str(v).lower() for v in as_list(get_path(root, cond.get("path", "cidr_blocks")))]
        return any(v in OPEN_CIDRS for v in values) == bool(cond["cidr_open"])
    if "port_includes" in cond:
        low = _int(get_path(root, cond.get("from", "from_port")))
        high = _int(get_path(root, cond.get("to", "to_port")))
        if low is None and high is None:
            return False
        low = 0 if low is None else low
        # protocol "-1" rules use 0-0, which means every port
        high = 65535 if high is None or (high == 0 and low == 0) else high
        return any(low <= int(p) <= high for p in as_list(cond["port_includes"]))
    if "path" in cond:
        value = get_path(root, cond["path"])
        for op, expected in cond.items():
            if op == "path":
                continue
            if op == "equals" and not (value is not _MISSING and value == expected):
                return False
            if op == "not_equals" and value is not _MISSING and value == expected:
                return False
            if op == "in" and value not in as_list(expected):
                return False
            if op == "not_in" and value in as_list(expected):
                return False
            if op == "exists" and (value is not _MISSING) != bool(expected):
                return False
            if op == "truthy" and (value not in (_MISSING, None, False, "", 0, "false")) != bool(expected):
                return False
            if op == "matches" and not (isinstance(value, str) and re.search(expected, value)):
                return False
            if op == "lt" and not (_int(value) is not None and _int(value) < expected):
                return False
            if op == "gt" and not (_int(value) is not None and _int(value) > expected):
                return False
        return True
    raise ValueError(f"unknown condition: {cond}")


def scan(inventory: Inventory, rules: list[Rule], min_severity: str = "info") -> list[Finding]:
    floor = SEVERITY_ORDER[min_severity]
    findings: list[Finding] = []
    for rule in rules:
        if rule.rank < floor:
            continue
        if "__inventory__" in rule.resource_types:
            if evaluate(rule.when, {}, None, inventory):
                first = inventory.resources[0] if inventory.resources else None
                findings.append(Finding(rule, "(estate)", first.file if first else "", 1))
            continue
        for resource in inventory.of_type(*rule.resource_types):
            if evaluate(rule.when, resource.values, resource, inventory):
                findings.append(Finding(rule, resource.address, resource.file, resource.line, resource))
    findings.sort(key=lambda f: (-f.rule.rank, f.rule.id, f.address))
    return findings
