# Appendix B: CloudGuard Rule Catalogue

This appendix lists every rule in CloudGuard's rule set. It is generated from the YAML files in `cloudguard/rules/` by `tools/generate_rule_catalogue.py`, and a test fails if it falls out of date, so the report always matches the code. Each rule's remediation advice and example fix are in the rule file and in the scanner's HTML report.

The catalogue contains 39 rules: 10 critical, 18 high, 9 medium, 2 low.

## Storage exposure

| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |
| --- | --- | --- | --- | --- |
| CG-AZ-ST-001 | critical | Azure blob container allows anonymous public access | AC-3, SC-7 | T1530 |
| CG-S3-001 | critical | S3 bucket ACL grants public access | AC-3, AC-6, SC-7 | T1530 |
| CG-S3-004 | critical | S3 bucket policy allows access to everyone | AC-3, AC-6 | T1530 |
| CG-AZ-ST-002 | high | Storage account does not disable public blob access | AC-3, CM-6 | T1530 |
| CG-S3-002 | high | S3 bucket has no public access block | AC-3, SC-7, CM-6 | T1530 |
| CG-S3-003 | high | S3 public access block is only partly enabled | AC-3, SC-7, CM-6 | T1530 |

## Identity and access

| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |
| --- | --- | --- | --- | --- |
| CG-IAM-001 | critical | IAM policy grants full administrator access ("*" on "*") | AC-6, AC-2 | T1078.004, T1098 |
| CG-IAM-005 | critical | IAM role can be assumed by any AWS principal | AC-3, AC-6 | T1078.004 |
| CG-AKS-002 | high | AKS cluster has Kubernetes RBAC disabled | AC-3, AC-6 | T1078.004 |
| CG-IAM-002 | high | IAM policy grants broad read access to all S3 buckets | AC-6 | T1530, T1078.004 |
| CG-IAM-004 | high | AWS managed AdministratorAccess policy is attached | AC-6, AC-2 | T1078.004 |
| CG-IAM-003 | medium | Long-lived IAM user access key is created | IA-5, AC-2 | T1552.001, T1078.004 |

## Network exposure

| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |
| --- | --- | --- | --- | --- |
| CG-AZ-NET-001 | critical | Network security group allows SSH, RDP or any port from the internet | SC-7, AC-17 | T1133, T1190 |
| CG-AZ-SQL-001 | critical | Azure SQL firewall allows the entire internet | SC-7, AC-3 | T1190 |
| CG-NET-001 | critical | Security group allows SSH or RDP from the internet | SC-7, AC-17 | T1133, T1190 |
| CG-NET-003 | critical | Security group exposes a database port to the internet | SC-7, AC-3 | T1190, T1530 |
| CG-RDS-001 | critical | RDS database is publicly accessible | SC-7, AC-3 | T1190 |
| CG-AKS-001 | high | AKS API server is reachable from any address | SC-7, AC-17 | T1133 |
| CG-AZ-SQL-002 | high | Azure SQL server allows public network access | SC-7 | - |
| CG-EKS-001 | high | EKS API endpoint is open to the whole internet | SC-7, AC-17 | T1133 |
| CG-NET-002 | high | Security group allows all ports from the internet | SC-7 | T1190 |
| CG-EC2-002 | medium | EC2 instance has a public IP address | SC-7 | T1190 |

## Compute and metadata

| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |
| --- | --- | --- | --- | --- |
| CG-EC2-001 | high | EC2 instance allows IMDSv1 (session tokens not required) | AC-6, SC-7 | T1552.005 |

## Secrets

| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |
| --- | --- | --- | --- | --- |
| CG-EC2-003 | high | Secret hard-coded in instance user data | IA-5, SC-28 | T1552.001, T1552.005 |
| CG-LAMBDA-001 | high | Secret hard-coded in Lambda environment variables | IA-5, SC-28 | T1552.001 |

## Data protection

| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |
| --- | --- | --- | --- | --- |
| CG-AZ-ST-004 | high | Storage account allows unencrypted HTTP traffic | SC-8 | - |
| CG-RDS-002 | high | RDS storage is not encrypted | SC-28, SC-12 | - |
| CG-AZ-ST-003 | medium | Storage account accepts TLS versions below 1.2 | SC-8, SC-13 | - |
| CG-EBS-001 | medium | EBS volume is not encrypted | SC-28 | - |
| CG-KMS-001 | medium | KMS key rotation is disabled | SC-12 | - |
| CG-S3-005 | medium | S3 bucket has no default encryption configuration | SC-28, SC-12 | - |

## Logging and monitoring

| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |
| --- | --- | --- | --- | --- |
| CG-LOG-001 | high | No CloudTrail trail is defined | AU-2, AU-12 | T1562.008 |
| CG-LOG-002 | high | CloudTrail trail is not multi-region | AU-2, AU-12 | T1562.008 |
| CG-LOG-004 | high | CloudTrail logging is switched off | AU-2, AU-12 | T1562.008 |
| CG-LOG-003 | medium | CloudTrail log file validation is disabled | AU-9 | T1070 |
| CG-VPC-001 | low | VPC has no flow logs | AU-12, SI-4 | - |

## Resilience

| Rule | Severity | Finding | NIST SP 800-53 | ATT&CK |
| --- | --- | --- | --- | --- |
| CG-AZ-KV-001 | medium | Key Vault purge protection is disabled | CP-9, SC-12 | T1485 |
| CG-RDS-003 | medium | RDS automated backups are disabled or shorter than 7 days | CP-9 | T1485, T1490 |
| CG-S3-006 | low | S3 bucket has versioning disabled | CP-9, SI-12 | T1485 |
