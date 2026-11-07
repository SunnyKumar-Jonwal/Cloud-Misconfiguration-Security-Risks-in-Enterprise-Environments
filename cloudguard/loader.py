"""Load Terraform configuration into a flat list of resources.

The scanner reads ``.tf`` files directly with python-hcl2, so it can run on a
pull request before anything is deployed ("shift left"). Values are
normalised so that rules can compare plain Python values:

* string quotes are stripped
* ``jsonencode({...})`` policies are parsed into dictionaries
* heredoc JSON policies are parsed into dictionaries
* references such as ``aws_iam_role.app.name`` are kept as text and can be
  resolved to the resource they point at with :meth:`Inventory.resolve`
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import hcl2
from hcl2.utils import SerializationOptions

OPTIONS = SerializationOptions(strip_string_quotes=True, preserve_heredocs=False, with_comments=False)
REFERENCE_RE = re.compile(r"\$\{([a-z0-9_]+)\.([A-Za-z0-9_-]+)(?:\[[^\]]*\])?(?:\.([A-Za-z0-9_]+))?\}$")
JSONENCODE_RE = re.compile(r"^\$\{jsonencode\((.*)\)\}$", re.S)


@dataclass
class Resource:
    type: str
    name: str
    values: dict
    file: str
    line: int = 1
    tags: dict = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.type}.{self.name}"


def _parse_policy(value):
    """Turn a policy written as jsonencode() or a JSON heredoc into a dict."""
    if not isinstance(value, str):
        return value
    match = JSONENCODE_RE.match(value.strip())
    if match:
        try:
            parsed = hcl2.loads(f"x = {match.group(1)}", serialization_options=OPTIONS)["x"]
            return _normalise(parsed)
        except Exception:  # noqa: BLE001 - leave unparseable expressions as text
            return value
    text = value.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return value
    return value


def _normalise(value):
    if isinstance(value, dict):
        return {k: _normalise(v) for k, v in value.items() if not k.startswith("__")}
    if isinstance(value, list):
        return [_normalise(v) for v in value]
    if isinstance(value, str) and (value.startswith("${jsonencode(") or value.lstrip().startswith("{")):
        return _parse_policy(value)
    return value


def _line_of(text: str, rtype: str, name: str) -> int:
    match = re.search(rf'^[ \t]*resource\s+"{re.escape(rtype)}"\s+"{re.escape(name)}"', text, re.M)
    return text.count("\n", 0, match.start()) + 1 if match else 1


class Inventory:
    """All resources found in a Terraform directory, with reference lookup."""

    def __init__(self, resources: list[Resource]):
        self.resources = resources
        self.by_address = {r.address: r for r in resources}

    def of_type(self, *types: str) -> list[Resource]:
        return [r for r in self.resources if r.type in types]

    def resolve(self, value) -> Resource | None:
        """Return the resource a reference such as ``${aws_iam_role.app.name}`` points to."""
        if not isinstance(value, str):
            return None
        match = REFERENCE_RE.match(value.strip())
        if not match:
            return None
        return self.by_address.get(f"{match.group(1)}.{match.group(2)}")

    def refers_to(self, value, target: Resource) -> bool:
        """True if ``value`` references ``target`` or equals one of its identifying names."""
        if self.resolve(value) is target:
            return True
        names = {target.values.get(k) for k in ("bucket", "name", "id")} - {None}
        return isinstance(value, str) and value in names

    def __len__(self) -> int:
        return len(self.resources)


def load(path: str | Path) -> Inventory:
    """Load every ``.tf`` file in ``path`` (a directory or a single file)."""
    path = Path(path)
    files = sorted(path.rglob("*.tf")) if path.is_dir() else [path]
    resources: list[Resource] = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        data = hcl2.loads(text, serialization_options=OPTIONS)
        for block in data.get("resource", []):
            for rtype, named in block.items():
                for name, body in named.items():
                    values = _normalise(body)
                    tags = values.get("tags") if isinstance(values.get("tags"), dict) else {}
                    resources.append(Resource(rtype, name, values, str(file), _line_of(text, rtype, name), tags))
    return Inventory(resources)
