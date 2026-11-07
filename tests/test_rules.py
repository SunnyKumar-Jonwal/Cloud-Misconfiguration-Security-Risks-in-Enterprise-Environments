"""Every CloudGuard rule must fire on a vulnerable snippet and stay silent on a safe one."""

import textwrap

import pytest

from cloudguard.engine import load_rules, scan
from cloudguard.loader import load

RULES = load_rules()

# Placed in front of every snippet so that estate-wide rules (CloudTrail) do not add noise.
TRAIL = '''
resource "aws_cloudtrail" "t" {
  name = "t"
  s3_bucket_name = "logs"
  is_multi_region_trail = true
  enable_log_file_validation = true
}
'''


def fired(tmp_path, hcl: str) -> set[str]:
    (tmp_path / "main.tf").write_text(TRAIL + textwrap.dedent(hcl), encoding="utf-8")
    return {f.rule.id for f in scan(load(tmp_path), RULES)}


BUCKET_SAFE_EXTRAS = '''
resource "aws_s3_bucket_public_access_block" "b" {
  bucket = aws_s3_bucket.b.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "b" {
  bucket = aws_s3_bucket.b.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}
resource "aws_s3_bucket_versioning" "b" {
  bucket = aws_s3_bucket.b.id
  versioning_configuration { status = "Enabled" }
}
'''

CASES = {
    "CG-S3-001": ('resource "aws_s3_bucket_acl" "a" {\n  bucket = "b"\n  acl = "public-read"\n}',
                  'resource "aws_s3_bucket_acl" "a" {\n  bucket = "b"\n  acl = "private"\n}'),
    "CG-S3-002": ('resource "aws_s3_bucket" "b" { bucket = "data" }',
                  'resource "aws_s3_bucket" "b" { bucket = "data" }' + BUCKET_SAFE_EXTRAS),
    "CG-S3-003": ('resource "aws_s3_bucket_public_access_block" "p" {\n  bucket = "b"\n  block_public_acls = true\n'
                  '  block_public_policy = false\n  ignore_public_acls = true\n  restrict_public_buckets = true\n}',
                  'resource "aws_s3_bucket_public_access_block" "p" {\n  bucket = "b"\n  block_public_acls = true\n'
                  '  block_public_policy = true\n  ignore_public_acls = true\n  restrict_public_buckets = true\n}'),
    "CG-S3-004": ('resource "aws_s3_bucket_policy" "p" {\n  bucket = "b"\n  policy = jsonencode({ Statement = [{ Effect = "Allow",'
                  ' Principal = "*", Action = "s3:GetObject", Resource = "arn:aws:s3:::b/*" }] })\n}',
                  'resource "aws_s3_bucket_policy" "p" {\n  bucket = "b"\n  policy = jsonencode({ Statement = [{ Effect = "Allow",'
                  ' Principal = "*", Action = "s3:GetObject", Resource = "arn:aws:s3:::b/*",'
                  ' Condition = { StringEquals = { "aws:SourceVpce" = "vpce-1" } } }] })\n}'),
    "CG-S3-005": ('resource "aws_s3_bucket" "b" { bucket = "data" }',
                  'resource "aws_s3_bucket" "b" { bucket = "data" }' + BUCKET_SAFE_EXTRAS),
    "CG-S3-006": ('resource "aws_s3_bucket" "b" { bucket = "data" }',
                  'resource "aws_s3_bucket" "b" { bucket = "data" }' + BUCKET_SAFE_EXTRAS),
    "CG-AZ-ST-001": ('resource "azurerm_storage_container" "c" {\n  name = "c"\n  container_access_type = "blob"\n}',
                     'resource "azurerm_storage_container" "c" {\n  name = "c"\n  container_access_type = "private"\n}'),
    "CG-AZ-ST-002": ('resource "azurerm_storage_account" "s" { name = "s" }',
                     'resource "azurerm_storage_account" "s" {\n  name = "s"\n  allow_nested_items_to_be_public = false\n}'),
    "CG-AZ-ST-003": ('resource "azurerm_storage_account" "s" {\n  name = "s"\n  min_tls_version = "TLS1_1"\n}',
                     'resource "azurerm_storage_account" "s" {\n  name = "s"\n  min_tls_version = "TLS1_2"\n}'),
    "CG-AZ-ST-004": ('resource "azurerm_storage_account" "s" {\n  name = "s"\n  https_traffic_only_enabled = false\n}',
                     'resource "azurerm_storage_account" "s" {\n  name = "s"\n  https_traffic_only_enabled = true\n}'),
    "CG-IAM-001": ('resource "aws_iam_policy" "p" {\n  policy = jsonencode({ Statement = [{ Effect = "Allow", Action = "*", Resource = "*" }] })\n}',
                   'resource "aws_iam_policy" "p" {\n  policy = jsonencode({ Statement = [{ Effect = "Allow", Action = "ec2:Describe*", Resource = "*" }] })\n}'),
    "CG-IAM-002": ('resource "aws_iam_role_policy" "p" {\n  policy = jsonencode({ Statement = [{ Effect = "Allow", Action = "s3:Get*", Resource = "*" }] })\n}',
                   'resource "aws_iam_role_policy" "p" {\n  policy = jsonencode({ Statement = [{ Effect = "Allow", Action = "s3:GetObject",'
                   ' Resource = "arn:aws:s3:::app-assets/*" }] })\n}'),
    "CG-IAM-003": ('resource "aws_iam_access_key" "k" { user = "ci" }', 'resource "aws_iam_user" "u" { name = "ci" }'),
    "CG-IAM-004": ('resource "aws_iam_role_policy_attachment" "a" {\n  role = "r"\n  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"\n}',
                   'resource "aws_iam_role_policy_attachment" "a" {\n  role = "r"\n  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"\n}'),
    "CG-IAM-005": ('resource "aws_iam_role" "r" {\n  assume_role_policy = jsonencode({ Statement = [{ Effect = "Allow",'
                   ' Principal = { AWS = "*" }, Action = "sts:AssumeRole" }] })\n}',
                   'resource "aws_iam_role" "r" {\n  assume_role_policy = jsonencode({ Statement = [{ Effect = "Allow",'
                   ' Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })\n}'),
    "CG-NET-001": ('resource "aws_security_group" "g" {\n  ingress {\n    from_port = 22\n    to_port = 22\n    protocol = "tcp"\n'
                   '    cidr_blocks = ["0.0.0.0/0"]\n  }\n}',
                   'resource "aws_security_group" "g" {\n  ingress {\n    from_port = 22\n    to_port = 22\n    protocol = "tcp"\n'
                   '    cidr_blocks = ["10.0.0.0/8"]\n  }\n}'),
    "CG-NET-002": ('resource "aws_security_group" "g" {\n  ingress {\n    from_port = 0\n    to_port = 0\n    protocol = "-1"\n'
                   '    cidr_blocks = ["0.0.0.0/0"]\n  }\n}',
                   'resource "aws_security_group" "g" {\n  ingress {\n    from_port = 443\n    to_port = 443\n    protocol = "tcp"\n'
                   '    cidr_blocks = ["0.0.0.0/0"]\n  }\n}'),
    "CG-NET-003": ('resource "aws_security_group" "g" {\n  ingress {\n    from_port = 5432\n    to_port = 5432\n    protocol = "tcp"\n'
                   '    cidr_blocks = ["0.0.0.0/0"]\n  }\n}',
                   'resource "aws_security_group" "g" {\n  ingress {\n    from_port = 5432\n    to_port = 5432\n    protocol = "tcp"\n'
                   '    security_groups = ["sg-app"]\n  }\n}'),
    "CG-AZ-NET-001": ('resource "azurerm_network_security_rule" "r" {\n  direction = "Inbound"\n  access = "Allow"\n'
                      '  source_address_prefix = "Internet"\n  destination_port_range = "22"\n}',
                      'resource "azurerm_network_security_rule" "r" {\n  direction = "Inbound"\n  access = "Allow"\n'
                      '  source_address_prefix = "10.0.0.0/8"\n  destination_port_range = "22"\n}'),
    "CG-EC2-001": ('resource "aws_instance" "i" { ami = "ami-1" }',
                   'resource "aws_instance" "i" {\n  ami = "ami-1"\n  metadata_options { http_tokens = "required" }\n}'),
    "CG-EC2-002": ('resource "aws_instance" "i" {\n  ami = "ami-1"\n  associate_public_ip_address = true\n'
                   '  metadata_options { http_tokens = "required" }\n}',
                   'resource "aws_instance" "i" {\n  ami = "ami-1"\n  associate_public_ip_address = false\n'
                   '  metadata_options { http_tokens = "required" }\n}'),
    "CG-EC2-003": ('resource "aws_launch_template" "t" {\n  user_data = "export DB_PASSWORD=hunter22hunter"\n'
                   '  metadata_options { http_tokens = "required" }\n}',
                   'resource "aws_launch_template" "t" {\n  user_data = "export DB_SECRET=arn:aws:secretsmanager:ap-south-1:1:secret:app/db"\n'
                   '  metadata_options { http_tokens = "required" }\n}'),
    "CG-LAMBDA-001": ('resource "aws_lambda_function" "f" {\n  environment {\n    variables = { API_TOKEN = "abc123xyz789" }\n  }\n}',
                      'resource "aws_lambda_function" "f" {\n  environment {\n    variables = { API_TOKEN_ARN = aws_secretsmanager_secret.s.arn }\n  }\n}'),
    "CG-EBS-001": ('resource "aws_ebs_volume" "v" { size = 10 }',
                   'resource "aws_ebs_volume" "v" {\n  size = 10\n  encrypted = true\n}'),
    "CG-RDS-001": ('resource "aws_db_instance" "d" {\n  publicly_accessible = true\n  storage_encrypted = true\n  backup_retention_period = 7\n}',
                   'resource "aws_db_instance" "d" {\n  publicly_accessible = false\n  storage_encrypted = true\n  backup_retention_period = 7\n}'),
    "CG-RDS-002": ('resource "aws_db_instance" "d" {\n  storage_encrypted = false\n  backup_retention_period = 7\n}',
                   'resource "aws_db_instance" "d" {\n  storage_encrypted = true\n  backup_retention_period = 7\n}'),
    "CG-RDS-003": ('resource "aws_db_instance" "d" {\n  storage_encrypted = true\n  backup_retention_period = 1\n}',
                   'resource "aws_db_instance" "d" {\n  storage_encrypted = true\n  backup_retention_period = 14\n}'),
    "CG-KMS-001": ('resource "aws_kms_key" "k" { description = "k" }',
                   'resource "aws_kms_key" "k" {\n  description = "k"\n  enable_key_rotation = true\n}'),
    "CG-AZ-SQL-001": ('resource "azurerm_mssql_firewall_rule" "f" {\n  start_ip_address = "0.0.0.0"\n  end_ip_address = "255.255.255.255"\n}',
                      'resource "azurerm_mssql_firewall_rule" "f" {\n  start_ip_address = "10.0.0.4"\n  end_ip_address = "10.0.0.4"\n}'),
    "CG-AZ-SQL-002": ('resource "azurerm_mssql_server" "s" { name = "s" }',
                      'resource "azurerm_mssql_server" "s" {\n  name = "s"\n  public_network_access_enabled = false\n}'),
    "CG-AZ-KV-001": ('resource "azurerm_key_vault" "k" { name = "k" }',
                     'resource "azurerm_key_vault" "k" {\n  name = "k"\n  purge_protection_enabled = true\n}'),
    "CG-LOG-002": ('resource "aws_cloudtrail" "x" {\n  name = "x"\n  is_multi_region_trail = false\n  enable_log_file_validation = true\n}',
                   'resource "aws_cloudtrail" "x" {\n  name = "x"\n  is_multi_region_trail = true\n  enable_log_file_validation = true\n}'),
    "CG-LOG-003": ('resource "aws_cloudtrail" "x" {\n  name = "x"\n  is_multi_region_trail = true\n}',
                   'resource "aws_cloudtrail" "x" {\n  name = "x"\n  is_multi_region_trail = true\n  enable_log_file_validation = true\n}'),
    "CG-LOG-004": ('resource "aws_cloudtrail" "x" {\n  name = "x"\n  is_multi_region_trail = true\n  enable_log_file_validation = true\n'
                   '  enable_logging = false\n}',
                   'resource "aws_cloudtrail" "x" {\n  name = "x"\n  is_multi_region_trail = true\n  enable_log_file_validation = true\n'
                   '  enable_logging = true\n}'),
    "CG-VPC-001": ('resource "aws_vpc" "v" { cidr_block = "10.0.0.0/16" }',
                   'resource "aws_vpc" "v" { cidr_block = "10.0.0.0/16" }\n'
                   'resource "aws_flow_log" "f" {\n  vpc_id = aws_vpc.v.id\n  traffic_type = "ALL"\n}'),
    "CG-EKS-001": ('resource "aws_eks_cluster" "e" {\n  vpc_config { endpoint_public_access = true }\n}',
                   'resource "aws_eks_cluster" "e" {\n  vpc_config {\n    endpoint_public_access = true\n'
                   '    public_access_cidrs = ["203.0.113.0/24"]\n  }\n}'),
    "CG-AKS-001": ('resource "azurerm_kubernetes_cluster" "k" { name = "k" }',
                   'resource "azurerm_kubernetes_cluster" "k" {\n  name = "k"\n  private_cluster_enabled = true\n}'),
    "CG-AKS-002": ('resource "azurerm_kubernetes_cluster" "k" {\n  private_cluster_enabled = true\n'
                   '  role_based_access_control_enabled = false\n}',
                   'resource "azurerm_kubernetes_cluster" "k" {\n  private_cluster_enabled = true\n'
                   '  role_based_access_control_enabled = true\n}'),
}


def test_every_rule_has_a_test_case():
    # CG-LOG-001 is estate-wide and tested separately below.
    assert {r.id for r in RULES} - set(CASES) == {"CG-LOG-001"}


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_rule_fires_on_vulnerable_snippet(tmp_path, rule_id):
    vulnerable, _ = CASES[rule_id]
    assert rule_id in fired(tmp_path, vulnerable)


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_rule_is_silent_on_safe_snippet(tmp_path, rule_id):
    _, safe = CASES[rule_id]
    assert rule_id not in fired(tmp_path, safe)


def test_missing_cloudtrail_is_reported_once_for_aws_estates(tmp_path):
    (tmp_path / "main.tf").write_text('resource "aws_s3_bucket" "b" { bucket = "x" }', encoding="utf-8")
    findings = [f for f in scan(load(tmp_path), RULES) if f.rule.id == "CG-LOG-001"]
    assert len(findings) == 1 and findings[0].address == "(estate)"


def test_missing_cloudtrail_is_not_reported_for_azure_only_estates(tmp_path):
    (tmp_path / "main.tf").write_text('resource "azurerm_storage_account" "s" { name = "s" }', encoding="utf-8")
    assert "CG-LOG-001" not in {f.rule.id for f in scan(load(tmp_path), RULES)}


def test_every_rule_documents_remediation_and_mappings():
    for rule in RULES:
        assert rule.remediation and rule.fix.strip(), rule.id
        assert rule.frameworks.get("nist_800_53"), rule.id
