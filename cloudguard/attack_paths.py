"""Attack-path analysis: link single misconfigurations into exploitable chains.

A rule looks at one resource. Real breaches chain several weaknesses that
are each "only medium" on their own. This module follows references
between resources (instance -> instance profile -> role -> policies ->
buckets) and reports four chains seen in the case studies of Chapter 4:

AP-1  Internet -> instance with IMDSv1 -> role that can read S3 -> sensitive
      bucket (the Capital One pattern)
AP-2  Anonymous internet -> publicly readable bucket or Blob container
      (Verizon/NICE, Pegasus Airlines, BlueBleed, Toyota)
AP-3  Long-lived access key -> user with administrator rights (leaked keys,
      as with Tesla's exposed console and Toyota's key on GitHub)
AP-4  Internet -> security group open on a database port -> publicly
      accessible database
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .engine import OPEN_CIDRS, _covers, _literal_in, _principal_public, as_list, get_path
from .loader import Inventory, Resource

SENSITIVE_TAG_VALUES = {"confidential", "restricted", "secret", "pii", "customer-pii", "financial"}
DB_PORTS = {3306, 5432, 1433, 1521, 27017, 6379}
ADMIN_ARN = "arn:aws:iam::aws:policy/AdministratorAccess"


@dataclass
class Step:
    description: str
    address: str = ""
    technique: str = ""


@dataclass
class AttackPath:
    id: str
    title: str
    severity: str
    pattern: str
    steps: list[Step] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "severity": self.severity, "pattern": self.pattern,
                "steps": [s.__dict__ for s in self.steps]}


def _is_sensitive(resource: Resource) -> bool:
    return any(str(v).lower() in SENSITIVE_TAG_VALUES for v in resource.tags.values())


def _open_ingress_ports(sg: Resource) -> list[tuple[int, int]]:
    ports = []
    for rule in as_list(sg.values.get("ingress")):
        if any(str(c).lower() in OPEN_CIDRS for c in as_list(rule.get("cidr_blocks"))):
            low, high = int(rule.get("from_port", 0) or 0), int(rule.get("to_port", 0) or 0)
            if str(rule.get("protocol")) == "-1" or (low == 0 and high == 0):
                low, high = 0, 65535
            ports.append((low, high))
    return ports


def _role_statements(inv: Inventory, role: Resource) -> list[tuple[str, dict]]:
    """All policy statements granted to a role, with the address they come from."""
    statements = []
    for rp in inv.of_type("aws_iam_role_policy"):
        if inv.refers_to(rp.values.get("role"), role):
            for st in as_list(get_path(rp.values, "policy.Statement")):
                statements.append((rp.address, st))
    for att in inv.of_type("aws_iam_role_policy_attachment"):
        if not inv.refers_to(att.values.get("role"), role):
            continue
        arn = att.values.get("policy_arn")
        if arn == ADMIN_ARN:
            statements.append((att.address, {"Effect": "Allow", "Action": "*", "Resource": "*"}))
        policy = inv.resolve(arn)
        if policy is not None:
            for st in as_list(get_path(policy.values, "policy.Statement")):
                statements.append((policy.address, st))
    return statements


def _readable_buckets(inv: Inventory, statements) -> tuple[list[Resource], str]:
    """Buckets the statements allow s3:GetObject on, and the granting policy."""
    readable: list[Resource] = []
    source = ""
    for address, st in statements:
        if str(st.get("Effect", "")).lower() != "allow" or not _covers(st.get("Action"), "s3:GetObject"):
            continue
        for bucket in inv.of_type("aws_s3_bucket"):
            name = bucket.values.get("bucket", "")
            arns = ["*", "arn:aws:s3:::*", "arn:aws:s3:::*/*", f"arn:aws:s3:::{name}", f"arn:aws:s3:::{name}/*"]
            if _literal_in(st.get("Resource"), arns) and bucket not in readable:
                readable.append(bucket)
                source = source or address
    return readable, source


def _capital_one_paths(inv: Inventory) -> list[AttackPath]:
    paths = []
    for instance in inv.of_type("aws_instance"):
        if get_path(instance.values, "metadata_options.0.http_tokens") == "required":
            continue
        groups = [inv.resolve(g) for g in as_list(instance.values.get("vpc_security_group_ids"))]
        open_ports = [p for g in groups if g is not None for p in _open_ingress_ports(g)]
        public = instance.values.get("associate_public_ip_address") is True
        if not (public and open_ports):
            continue
        profile = inv.resolve(instance.values.get("iam_instance_profile"))
        role = inv.resolve(profile.values.get("role")) if profile else None
        if role is None:
            continue
        buckets, source = _readable_buckets(inv, _role_statements(inv, role))
        sensitive = [b for b in buckets if _is_sensitive(b)]
        if not sensitive:
            continue
        ports = ", ".join(f"{lo}" if lo == hi else f"{lo}-{hi}" for lo, hi in open_ports)
        paths.append(AttackPath(
            "AP-1", f"Internet to sensitive S3 data through {instance.address}", "critical", "Capital One (2019)", [
                Step(f"Attacker reaches the instance's public IP on port(s) {ports}", instance.address, "T1190"),
                Step("An SSRF flaw makes the instance call the metadata service; IMDSv1 needs no session token",
                     instance.address, "T1552.005"),
                Step(f"The metadata service returns temporary credentials for role {role.values.get('name', role.name)}",
                     role.address, "T1078.004"),
                Step("The role's policy allows s3:GetObject on " + ("every bucket" if len(buckets) > 1 else "the bucket"),
                     source, "T1530"),
                Step("Sensitive data can be copied: " + ", ".join(b.values.get("bucket", b.name) for b in sensitive),
                     ", ".join(b.address for b in sensitive), "T1530"),
            ]))
    return paths


def _public_data_paths(inv: Inventory) -> list[AttackPath]:
    paths = []
    for bucket in inv.of_type("aws_s3_bucket"):
        reasons = []
        for acl in inv.of_type("aws_s3_bucket_acl"):
            if inv.refers_to(acl.values.get("bucket"), bucket) and acl.values.get("acl") in ("public-read", "public-read-write"):
                reasons.append(Step(f"Bucket ACL is {acl.values['acl']}", acl.address, "T1530"))
        for pol in inv.of_type("aws_s3_bucket_policy"):
            if not inv.refers_to(pol.values.get("bucket"), bucket):
                continue
            for st in as_list(get_path(pol.values, "policy.Statement")):
                if str(st.get("Effect")).lower() == "allow" and _principal_public(st.get("Principal")) and not st.get("Condition"):
                    reasons.append(Step("Bucket policy allows Principal \"*\"", pol.address, "T1530"))
        if reasons:
            label = "sensitive " if _is_sensitive(bucket) else ""
            paths.append(AttackPath(
                "AP-2", f"Anonymous internet access to {label}bucket {bucket.values.get('bucket', bucket.name)}",
                "critical" if _is_sensitive(bucket) else "high", "Verizon/NICE (2017), Pegasus Airlines (2022)",
                [Step("Anyone on the internet requests objects without credentials", "", "T1530")] + reasons
                + [Step("Objects are downloadable" + (" (tagged as sensitive)" if label else ""), bucket.address, "T1530")]))
    for container in inv.of_type("azurerm_storage_container"):
        if container.values.get("container_access_type") in ("blob", "container"):
            listing = container.values["container_access_type"] == "container"
            paths.append(AttackPath(
                "AP-2", f"Anonymous internet access to Blob container {container.values.get('name', container.name)}",
                "critical" if listing else "high", "Microsoft BlueBleed (2022)", [
                    Step("Anyone on the internet requests blobs without credentials", "", "T1530"),
                    Step(f"Container access type is '{container.values['container_access_type']}'"
                         + (" (blobs can also be listed)" if listing else ""), container.address, "T1530"),
                ]))
    return paths


def _key_to_admin_paths(inv: Inventory) -> list[AttackPath]:
    paths = []
    for key in inv.of_type("aws_iam_access_key"):
        user = inv.resolve(key.values.get("user"))
        if user is None:
            continue
        admin = [a for a in inv.of_type("aws_iam_user_policy_attachment")
                 if inv.refers_to(a.values.get("user"), user) and a.values.get("policy_arn") == ADMIN_ARN]
        if admin:
            paths.append(AttackPath(
                "AP-3", f"Leaked access key gives full control of the account ({user.address})", "critical",
                "Tesla (2018), Toyota T-Connect key on GitHub (2022)", [
                    Step("A static access key exists and can leak through code, CI logs or a laptop", key.address,
                         "T1552.001"),
                    Step("The key belongs to an IAM user with AdministratorAccess", admin[0].address, "T1078.004"),
                    Step("The holder of the key can read all data, create users and disable logging", "", "T1098"),
                ]))
    return paths


def _database_paths(inv: Inventory) -> list[AttackPath]:
    paths = []
    for db in inv.of_type("aws_db_instance"):
        if db.values.get("publicly_accessible") is not True:
            continue
        for ref in as_list(db.values.get("vpc_security_group_ids")):
            sg = inv.resolve(ref)
            if sg is None:
                continue
            hits = [port for lo, hi in _open_ingress_ports(sg) for port in DB_PORTS if lo <= port <= hi]
            if hits:
                paths.append(AttackPath(
                    "AP-4", f"Internet to database {db.address}", "critical", "Exposed databases (Section 3.5)", [
                        Step(f"Security group {sg.address} allows port {hits[0]} from 0.0.0.0/0", sg.address, "T1190"),
                        Step("The database has a public endpoint", db.address, "T1190"),
                        Step("Credential stuffing or an engine vulnerability gives direct access to the data", db.address,
                             "T1110"),
                    ]))
                break
    return paths


def find_paths(inventory: Inventory) -> list[AttackPath]:
    return (_capital_one_paths(inventory) + _public_data_paths(inventory)
            + _key_to_admin_paths(inventory) + _database_paths(inventory))
