# CloudGuard: Implementation and Results

## 6.1 Objectives of the Prototype

Chapter 5 argued that misconfigurations are cheapest to stop before they are deployed, and that findings should be prioritised by the attack paths they create. To test these ideas, a prototype scanner, CloudGuard, was built. It had five objectives:

1. To detect the misconfiguration classes of Chapter 3 directly in Terraform code, before anything is deployed, for both AWS and Azure
2. To keep every rule as reviewable data (policy as code) rather than as program logic
3. To link findings across resources into attack paths that match the breaches of Chapter 4
4. To detect configuration drift and explain which change caused each new finding
5. To compare its results honestly with an established open-source scanner on the same code

CloudGuard is a research prototype. It reads Terraform files and never connects to a cloud account, so it can be run safely on any repository, but it also cannot see settings that exist only in a live environment. Section 6.9 discusses this.

## 6.2 System Design

Figure 6.1 shows the architecture. Terraform files are parsed into an inventory of resources. The rule engine evaluates each YAML rule against the resources it applies to, the attack-path analyser follows references between resources, and the drift comparator scans a baseline and a current version side by side. Reporters turn the results into a terminal table, JSON, SARIF or HTML, and the exit code tells a CI pipeline whether to block the change.

![Figure 6.1: Architecture of the CloudGuard scanner](figures/fig-6-1-cloudguard-architecture.png)

## 6.3 Technology Stack and Modules

CloudGuard is written in Python 3.12. It depends on python-hcl2 to parse Terraform's HCL syntax and on PyYAML to read the rules; everything else uses the standard library. Table 6.1 lists the modules.

Table 6.1: Modules of the CloudGuard prototype

| Module | Responsibility |
| --- | --- |
| `loader.py` | Parse `.tf` files, normalise values, parse `jsonencode()` and heredoc policies, resolve references, record line numbers |
| `engine.py` | Load YAML rules and evaluate their conditions against the inventory |
| `rules/*.yaml` | 39 rules in seven files, grouped by misconfiguration class |
| `attack_paths.py` | Find the four attack-path patterns AP-1 to AP-4 |
| `drift.py` | Compare a baseline with the current configuration |
| `reporters.py` | Table, JSON, SARIF 2.1.0 and HTML output |
| `cli.py` | The `scan`, `paths`, `drift` and `rules` commands and their exit codes |

## 6.4 Rule Model

Each rule is a YAML document that states what it checks, how serious it is and how to fix it. The rule below detects instances that allow IMDSv1, the setting at the centre of the Capital One breach [20].

```yaml
- id: CG-EC2-001
  title: EC2 instance allows IMDSv1 (session tokens not required)
  severity: high
  category: compute
  resource_types: [aws_instance, aws_launch_template]
  when:
    path: metadata_options.0.http_tokens
    not_equals: required
  remediation: Require IMDSv2 by setting http_tokens = "required".
  fix: |
    metadata_options {
      http_tokens                 = "required"
      http_put_response_hop_limit = 1
    }
  frameworks: {nist_800_53: [AC-6, SC-7], mitre_attack: [T1552.005]}
```

Conditions are built from a small set of operators: boolean combinators (`all`, `any`, `not`), attribute tests (`equals`, `in`, `exists` and others), list tests (`any_item`), network tests (`cidr_open`, `port_includes`), IAM statement tests (`action_is`, `action_covers`, `resource_in`, `principal_public`, `has_condition`), relationship tests (`missing_related`) and secret detection (`secret_in`). Because the rules are data, a security team can review, add or tune them without changing the engine, which is the main advantage of policy as code [19]. Table 6.2 summarises the rule set.

Table 6.2: CloudGuard rules by misconfiguration class and severity

| Class | Rules | Critical | High | Medium | Low | Example |
| --- | :---: | :---: | :---: | :---: | :---: | --- |
| Storage exposure | 6 | 3 | 3 | 0 | 0 | Public S3 ACL or Blob container |
| Identity | 6 | 2 | 3 | 1 | 0 | Policy granting `*` on `*` |
| Network exposure | 10 | 5 | 4 | 1 | 0 | SSH or RDP open to the internet |
| Compute and secrets | 3 | 0 | 3 | 0 | 0 | IMDSv1, password in user data |
| Data protection | 6 | 0 | 2 | 4 | 0 | Unencrypted RDS storage |
| Logging | 5 | 0 | 3 | 1 | 1 | Single-region CloudTrail |
| Resilience | 3 | 0 | 0 | 2 | 1 | Database backups disabled |
| **Total** | **39** | **10** | **18** | **9** | **2** | 29 AWS and 10 Azure rules, 32 resource types |

Every rule is mapped to NIST SP 800-53 controls [8] (17 controls in total, including AC-3, AC-6, SC-7, SC-28 and AU-2) and, where an attacker technique applies, to MITRE ATT&CK [11] (11 techniques, including T1530 Data from Cloud Storage and T1552.005 Cloud Instance Metadata API).

## 6.5 Implementation Details

### 6.5.1 Parsing Terraform

python-hcl2 returns strings with their quotes, policies written with `jsonencode()` as unparsed HCL text, and heredoc policies as raw text. The loader strips quotes, re-parses the body of `jsonencode()` as an HCL object, and parses heredocs as JSON, so that a rule can inspect a policy's `Statement` list directly. References such as `aws_iam_role.web.name` are kept as text and resolved to the resource they point at when a rule or the path analyser needs them. The loader records the line on which each `resource` block starts, so that SARIF results point at the right line in the pull request.

### 6.5.2 Evaluating Rules

The engine walks each rule's condition tree against every resource of the listed types. IAM checks needed special care. A rule looking for "full administrator access" must match a policy whose action is literally `*`, while a rule looking for "can read any bucket" must match any action pattern that *covers* `s3:GetObject`, such as `s3:Get*` or `*`. The engine therefore has separate operators for literal values (`action_is`) and for wildcard coverage (`action_covers`). Relationship rules check that a companion resource exists, for example that every bucket has a public access block that refers to it. One estate-wide rule reports a missing CloudTrail trail once for the whole configuration.

### 6.5.3 Attack Paths

The analyser follows references from an instance to its instance profile, then to the role, the role's inline and attached policies, and finally the buckets those policies allow it to read. It reports four patterns: AP-1 (internet, IMDSv1, a role with S3 read access and a bucket tagged as sensitive), AP-2 (a public bucket or Blob container), AP-3 (a static access key belonging to an administrator) and AP-4 (a public database behind an open database port). Each step carries the ATT&CK technique involved, so the output reads as an attack narrative rather than a list of settings.

### 6.5.4 Drift Detection

The drift module loads two directories, matches resources by address and compares their values attribute by attribute. It then scans both versions and reports the findings that are new in the current version, each linked to the attributes that changed on the same resource.

### 6.5.5 Reporting and CI Integration

The table output is meant for engineers, the HTML report for security reviewers, JSON for other tools and SARIF 2.1.0 [39] for code-scanning platforms that show results as annotations on the changed lines. The `scan` command exits with status 1 when a finding at or above the `--fail-on` severity (high by default) is present, so a pipeline can block the merge. The project's own GitHub Actions workflow scans the example estates on every pull request: the vulnerable estate must fail, the hardened estate must pass, the Capital One replay must produce an attack path and the drifted estate must report new findings.

## 6.6 Test Environments and Method

Four Terraform configurations were written for the evaluation. All are fictional and must not be deployed.

- **Vulnerable Acme Retail estate** (41 resources on AWS and Azure). It plants the misconfigurations from the case studies: a public customer-export bucket, an internet-facing instance with IMDSv1 whose role can read every bucket, SSH, RDP and MySQL open to the internet, a public unencrypted database without backups, an administrator CI user with a static key, a role anyone can assume, a public Blob container, an Azure SQL firewall rule allowing every address, and exposed EKS and AKS control planes.
- **Hardened estate** (46 resources). The same company with each rule's remediation applied, including private networking, IMDSv2, least privilege, OIDC federation for CI, encryption, backups and logging.
- **Drifted estate** (46 resources). The hardened estate after four unreviewed changes: emergency SSH from anywhere, a bucket policy and public access block loosened for a partner, IMDSv1 re-enabled for a legacy agent and CloudTrail logging switched off.
- **Capital One replay** (9 resources). A reconstruction of the configuration pattern publicly reported for the 2019 breach [21], with illustrative names.

The prototype was tested at three levels: 105 automated tests (an "it fires" and an "it stays silent" test for each rule, plus tests for the loader, reporters, attack paths, drift, command-line exit codes and the generated rule catalogue); runs on the four configurations; and a comparison with Checkov 3.4.3 [18], a widely used open-source IaC scanner, on the same files. The comparison is produced by `tools/compare_with_checkov.py`, so it can be repeated with any Checkov version.

## 6.7 Results

### 6.7.1 Findings per Estate

Table 6.3 summarises the scans.

Table 6.3: CloudGuard results on the four test configurations

| Configuration | Resources | Findings | Critical | High | Medium | Low | Attack paths |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Vulnerable | 41 | 40 | 12 | 17 | 9 | 2 | 5 |
| Hardened | 46 | 0 | 0 | 0 | 0 | 0 | 0 |
| Drifted | 46 | 5 | 2 | 3 | 0 | 0 | 1 |
| Capital One replay | 9 | 12 | 0 | 5 | 4 | 3 | 1 |

Every planted misconfiguration in the vulnerable estate was reported, and the hardened estate produced no findings. The largest class was network exposure (12 findings), followed by identity (7), storage exposure (6) and data protection (6). Ten findings were in the Azure part of the estate and thirty in the AWS part. Figure 6.2 shows the actual scan output; the hardened scan is in Appendix C.

![Figure 6.2: CloudGuard scan of the vulnerable Acme Retail estate (python -m cloudguard scan)](../docs/screenshots/02-scan-vulnerable.png)

### 6.7.2 Attack Paths

Table 6.4 lists the attack paths found.

Table 6.4: Attack paths reported by CloudGuard

| Configuration | Path | Description | Real-world pattern |
| --- | --- | --- | --- |
| Vulnerable | AP-1 | Public web instance (ports 443, 22), IMDSv1, role `acme-web-role` with `s3:GetObject` on `*`, confidential customer-export bucket | Capital One 2019 |
| Vulnerable | AP-2 | Customer-export bucket readable by anyone through its ACL and bucket policy | Verizon/NICE 2017, Pegasus 2022 |
| Vulnerable | AP-2 | Invoice Blob container listable by anyone | BlueBleed 2022 |
| Vulnerable | AP-3 | Static access key of a CI user with AdministratorAccess | Tesla 2018, Toyota 2022 |
| Vulnerable | AP-4 | MySQL open to 0.0.0.0/0 in front of a publicly accessible RDS database | SBI Quick 2019 |
| Drifted | AP-2 | Customer-export bucket made public by the drifted bucket policy | Drift after review |
| Capital One replay | AP-1 | Public WAF instance, IMDSv1, role with S3 read on `*`, two sensitive buckets (the public web-assets bucket is correctly excluded) | Capital One 2019 |

The Capital One replay illustrates why attack paths matter. Taken one by one, its worst findings are only *high*: IMDSv1, a broad S3 policy, buckets without public access blocks. No single rule calls the configuration critical. Linked together, the same findings form the chain that led to one of the largest cloud breaches on record. A test in the suite confirms that fixing any one link (requiring IMDSv2, removing the public IP or scoping the role to one bucket) breaks the path. Figure 6.3 shows the path as reported.

![Figure 6.3: The Capital One attack path reported by python -m cloudguard paths](../docs/screenshots/05-attack-path-capital-one.png)

The drifted estate shows the opposite effect. IMDSv1 was re-enabled on the web instance, but no AP-1 path appears, because the instance is still private and its role is still scoped to one prefix. The other layers of the hardened design contained the drift.

### 6.7.3 Drift Detection

Comparing the hardened baseline with the drifted estate, CloudGuard reported no added or removed resources, five changed resources and five new findings. Each was attributed to the attribute that caused it, as shown in Table 6.5 and Figure 6.4.

![Figure 6.4: Drift report comparing the hardened baseline with the drifted estate](../docs/screenshots/06-drift.png)

Table 6.5: New findings in the drifted estate and the changes that caused them

| New finding | Severity | Resource | Changed attribute |
| --- | --- | --- | --- |
| CG-NET-001 SSH or RDP open to the internet | Critical | `aws_security_group.web` | `ingress` |
| CG-S3-004 Bucket policy allows everyone | Critical | `aws_s3_bucket_policy.customer_exports` | `policy.Statement.0.Principal` |
| CG-EC2-001 IMDSv1 allowed | High | `aws_instance.web` | `metadata_options.0.http_tokens` |
| CG-LOG-004 CloudTrail logging switched off | High | `aws_cloudtrail.main` | `enable_logging` |
| CG-S3-003 Public access block partly disabled | High | `aws_s3_bucket_public_access_block.customer_exports` | `block_public_policy`, `restrict_public_buckets` |

### 6.7.4 Comparison with Checkov

Checkov evaluated 154 distinct checks on the vulnerable estate and reported 126 failures, against CloudGuard's 39 rules and 40 findings. For each CloudGuard finding, the comparison script looked for the Checkov check that tests the same issue. Table 6.6 summarises the outcome, and Figure 6.5 shows the comparison script's output for the issues Checkov did not detect. The full table is in `evaluation/checkov-comparison.md` in the repository.

Table 6.6: Did Checkov flag the issues CloudGuard found on the vulnerable estate?

| Outcome | Findings | Details |
| --- | :---: | --- |
| Checkov detected the same issue | 35 of 40 | Public storage, IAM, open SSH/RDP, IMDSv1, encryption, logging, Kubernetes exposure and others |
| Checkov's check ran and passed (missed) | 4 | MySQL port 3306 open to 0.0.0.0/0 (no default check for database ports); password in EC2 user data (`CKV_AWS_46`); token in Lambda environment (`CKV_AWS_45`); storage account with secure transfer disabled (`CKV_AZURE_3` reads the older attribute name `enable_https_traffic_only`, while azurerm 4.x uses `https_traffic_only_enabled`) |
| Only a related check | 1 | The static access key: Checkov flags the IAM user (`CKV_AWS_273`), not the key itself |

![Figure 6.5: Output of tools/compare_with_checkov.py, filtered to the totals and the issues Checkov missed](../docs/screenshots/09-checkov-comparison.png)

The comparison cuts both ways. Checkov missed four issues that CloudGuard caught, two of them high-severity hard-coded secrets and one critical network exposure. But Checkov's much larger library also reports many issues that CloudGuard does not check at all. On the *hardened* estate, where CloudGuard reports nothing, Checkov still reports 72 failures. Some are best-practice items (lifecycle rules, Multi-AZ, X-Ray tracing), but others are real security gaps outside CloudGuard's rule set, such as S3 access logging, CloudTrail encryption with a customer-managed key, EKS secrets encryption and control-plane logging, and SQL auditing. Neither tool links findings into attack paths the way CloudGuard's analyser does: none of the 32 Checkov failures on the Capital One replay describes the chain as a whole.

The practical conclusion matches Section 5.5: a broad, community-maintained scanner and a small set of organisation-specific rules and path checks complement each other, and either one used alone misses real problems.

### 6.7.5 Problems Found During Development

Building and testing CloudGuard exposed six defects. They are reported here because each is a type of mistake that any IaC scanner can make.

1. **Wildcard semantics in IAM rules.** The first version treated the rule pattern `*` as matching any action, so a policy granting only `s3:GetObject` was reported as full administrator access. Literal matching and wildcard coverage were then split into separate operators.
2. **ARNs mistaken for secrets.** The hardened estate's user data references a Secrets Manager ARN containing `:secret:acme/orders-db`, which the secret detector flagged. The safe practice was being reported as the unsafe one. ARNs are now removed before matching.
3. **Off-by-one line numbers.** The regular expression that finds each resource block also matched a preceding blank line, so SARIF results pointed one line too early.
4. **A missed attack path.** A Python set passed to a helper that expected a list caused the analyser to miss the Capital One path in the vulnerable estate, the very pattern it was built to find.
5. **A CI job that could never pass.** Generating the SARIF and HTML reports for the vulnerable estate returned exit code 1 (correctly, because it has findings), which failed the CI step. This was found by running the job locally with the same shell options before pushing.
6. **Version drift in a third-party check.** As described in Section 6.7.4, Checkov's secure-transfer check missed the issue because a provider attribute had been renamed. The same risk applies to every scanner, including CloudGuard, whenever a provider changes its schema.

Defects 1 to 4 were found by the "fires on vulnerable, silent on safe" test pairs and by running the scanner on complete estates. This supports the practice of keeping known-good and known-bad examples alongside every rule.

### 6.7.6 Performance

Parsing and scanning the 41-resource vulnerable estate took a median of about 48 milliseconds over 20 runs on the development machine. Checkov's whole run on the same directory took about 3 seconds, which includes starting a separate process and loading its full check library. Its attempts to contact its vendor's API were blocked in the test environment, so this figure is indicative only. Both are fast enough for a pull-request check, where the time to build and plan the infrastructure is usually much longer.

## 6.8 Discussion

The results support three claims from earlier chapters. First, the misconfigurations behind the case studies in Chapter 4 can be detected in code before deployment with simple, explainable rules: every one planted in the vulnerable estate was found, and the hardened estate passed cleanly. Second, attack-path analysis adds information that per-resource rules cannot provide: the Capital One replay is "high at worst" finding by finding but critical as a chain, and the analysis correctly showed both when the drift did break a defence and when it did not. Third, drift detection that explains *which change* introduced a finding turns a list of problems into actionable review comments.

The comparison with Checkov also carries a lesson about rule sets. A smaller, purpose-built rule set can catch things a large generic one misses, such as database ports or renamed attributes, while the large one covers far more ground. Rules decay as providers change their schemas, so every rule needs test cases that fail when it stops working.

## 6.9 Limitations

- CloudGuard reads Terraform only. It does not see resources created by hand in the console, by other tools or by the providers themselves, and it does not evaluate Terraform variables, modules from registries, `count`/`for_each` expansions or provider default values. A runtime CSPM is still needed (Section 5.7).
- The rule set has 39 rules, compared with hundreds in mature tools. It covers the classes in this report, not every cloud service.
- Attack-path analysis covers four patterns and AWS IAM only. It does not model network routing, resource policies on other services, or Azure role assignments.
- The test configurations were written by the author of the rules. The results show that the rules behave as designed on these examples, not that they are complete or free of false positives on real-world code.
- The comparison with Checkov is a single version on four small configurations; results with other versions or larger code bases may differ.
