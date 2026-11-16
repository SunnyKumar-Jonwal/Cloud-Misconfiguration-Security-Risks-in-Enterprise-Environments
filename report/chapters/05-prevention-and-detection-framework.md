# Prevention and Detection Framework

## 5.1 Design Principles

The taxonomy in Chapter 3 and the breaches in Chapter 4 point to six principles that shape every control in this chapter.

1. **Secure by default, not secure by effort.** A misconfiguration is usually a default nobody changed or a setting somebody relaxed. Controls should make the safe option the one that happens when nobody intervenes.
2. **Prevent at the organisation level, not resource by resource.** Settings such as S3 Block Public Access, IMDSv2 and encryption by default can be enforced for an entire account or tenant, so a single careless resource cannot undo them [32], [33], [34].
3. **Check configuration before it is deployed.** When infrastructure is defined as code, every change passes through a pull request, and that is the cheapest place to catch a mistake [15], [16].
4. **Assume drift and keep checking after deployment.** Emergency changes, console edits and new services mean that what is running slowly diverges from what was reviewed.
5. **Prioritise by attack path, not by finding count.** A medium finding that completes a chain to sensitive data matters more than a dozen unrelated high findings.
6. **Treat identity as the main perimeter.** In the cloud, credentials and permissions decide what an attacker can reach, so least privilege, short-lived credentials and MFA carry more weight than network controls [36], [37].

## 5.2 Framework Overview

The framework follows the life of a cloud resource from design to operation. Figure 5.1 shows its five stages and the identity and data-classification foundation they share.

![Figure 5.1: Lifecycle framework for preventing and detecting cloud misconfiguration](figures/fig-5-1-lifecycle-framework.png)

**Govern** decides who owns what and how data is classified. **Guardrail** enforces non-negotiable settings across the organisation. **Shift left** checks every infrastructure change in the pull request. **Monitor** watches the running estate for drift and attack paths. **Respond** detects misuse and fixes problems quickly. Each stage catches what the previous one missed, and the findings of later stages feed back into earlier ones as new rules and guardrails.

## 5.3 Govern: Ownership, Structure and Data Classification

- **Account and subscription structure.** Separate production, non-production, security tooling and log archive into different AWS accounts or Azure subscriptions under a management hierarchy (a "landing zone"). Separation limits the blast radius of a mistake: a development account with weak settings cannot expose production data.
- **Ownership and tagging.** Every resource carries an owner and a data-classification tag (for example `public`, `internal`, `confidential`, `restricted`). Tags let tools such as CloudGuard tell a public marketing bucket from a bucket of customer records, which was the difference between harmless and harmful exposure in several of the cases in Chapter 4.
- **Policy and exceptions.** Publish a cloud security standard based on the CIS Benchmarks [7] and the CSA Cloud Controls Matrix [10]. Every exception has an owner, a reason and an expiry date, so "temporary" changes such as the MySQL port in the Acme Retail example do not become permanent.
- **Regulatory alignment.** Map controls to ISO/IEC 27017 [9] and NIST SP 800-53 [8]. For Indian operations, the CERT-In directions require logs to be kept for 180 days and incidents to be reported within six hours [12], and the DPDP Act applies to personal data in the cloud [13].

## 5.4 Guardrail: Preventive Controls at Organisation Level

Guardrails stop a misconfiguration from being created at all, whatever the tool or person making the change.

- **AWS Service Control Policies (SCPs)** can deny actions across every account in an organisation, for example disabling CloudTrail, deleting log buckets, launching instances without IMDSv2 or leaving the approved regions [33].
- **Azure Policy** with the `deny` effect can block public blob access, storage accounts without secure transfer, public IP addresses on virtual machines or SQL servers with public network access [34].
- **Account-level defaults.** Enable S3 Block Public Access at account level, EBS encryption by default and IMDSv2 as the default for new instances. Since April 2023, new S3 buckets have Block Public Access enabled and ACLs disabled by default [32], which removes the most common cause of public buckets for new resources, but not for the existing buckets most enterprises already have.
- **Identity guardrails.** Enforce MFA for every human identity, including identities in test tenants and SaaS platforms, and block the creation of IAM users with long-lived access keys where federation is available. The Snowflake customer breaches and the Midnight Blizzard intrusion both started with accounts that did not have MFA [29], [30].

## 5.5 Shift Left: Checking Infrastructure as Code Before Deployment

Most enterprises now define cloud resources in Terraform, CloudFormation, Bicep or similar tools. Scanning this code in the pull request gives fast, cheap feedback to the engineer who made the change.

- **Policy as code.** Express security rules as data (CloudGuard's YAML rules, Open Policy Agent policies [19] or Checkov checks [18]) kept in version control, reviewed like any other code and tested against known-good and known-bad examples.
- **Gate on severity.** Block the merge for critical and high findings and report medium and low findings as warnings, so the gate is strict enough to matter but does not stop all work.
- **Report where engineers look.** Publish results in SARIF [39] so they appear as annotations on the changed lines of the pull request, and include the suggested fix with every finding.
- **Use more than one scanner.** Chapter 6 shows that two scanners with different rule sets miss different things. A broad open-source scanner plus a small set of organisation-specific rules covers more than either alone.

## 5.6 Identity and Access Controls

- **Least privilege by design.** Grant actions on specific resources, not `*` on `*`. Use AWS IAM Access Analyzer or equivalent tooling to find unused permissions and to generate policies from observed activity.
- **No long-lived keys.** Use roles and temporary credentials for workloads, and OpenID Connect federation for CI/CD pipelines, as the hardened Acme Retail estate does for its deployment pipeline. Scan code repositories for leaked keys; the Toyota T-Connect key published on GitHub shows how a key can remain exposed for years [38].
- **Protect the metadata service.** Require IMDSv2 so that an SSRF flaw in an application cannot be used to read instance credentials, the step that made the Capital One breach possible [20].
- **Trust policies.** Review who can assume each role. A trust policy with `Principal: "*"` makes a role available to every AWS account in the world.

## 5.7 Monitor: Runtime Posture and Drift

Not everything goes through infrastructure as code, and what does can drift after deployment.

- **Cloud Security Posture Management (CSPM).** Use the providers' native services or a commercial CSPM to evaluate the running configuration continuously against the same benchmarks used in the pipeline.
- **Drift detection.** Compare the running configuration with the approved baseline in version control and treat every difference as a change that needs review. CloudGuard's drift module shows how each new finding can be traced to the exact attribute that changed.
- **Attack-path prioritisation.** Correlate findings across resources and fix first the ones that complete a path from the internet to sensitive data.
- **Asset discovery.** Look for unmanaged resources, forgotten test environments and SaaS platforms holding enterprise data (Power Apps, Snowflake), which are often outside the scope of infrastructure-as-code scanning [25], [29].

## 5.8 Respond: Detection, Alerting and Remediation

- **Organisation-wide logging.** Send CloudTrail from every account and region, and the Azure activity log from every subscription, to a separate log-archive account that application teams cannot change. Protect the logs with validation and retention of at least 180 days [12].
- **Threat detection.** Enable managed detection services and alert on high-risk events, such as `StopLogging`, `PutBucketPolicy` with a public principal, `PutBucketPublicAccessBlock`, new access keys for privileged users, and use of instance credentials from outside the provider's network.
- **Automated remediation.** For a small set of unambiguous issues, such as a newly public bucket without an approved exception, fix the problem automatically and notify the owner. For everything else, open a ticket with the owner and a due date based on severity.
- **Incident readiness.** Write a cloud-specific incident playbook: revoke sessions and keys, preserve logs, snapshot affected resources, assess data exposure and meet regulatory reporting deadlines.

## 5.9 Mapping to Standards and Risks

Table 5.1 shows which risks from the register in Table 4.4 each stage addresses and how the stages relate to NIST SP 800-53 [8], the CSA Cloud Controls Matrix [10] and MITRE ATT&CK [11].

Table 5.1: Mapping of framework stages to risks and standards

| Stage | Main risks addressed | NIST SP 800-53 families | CSA CCM domains | ATT&CK techniques mitigated |
| --- | --- | --- | --- | --- |
| Govern | R9, R10 | PL, PM, RA, CM | GRC, DSP | (all, indirectly) |
| Guardrail | R1, R4, R5, R6, R11 | AC, SC, CM, IA | IAM, IVS, DSP | T1530, T1190, T1552.005, T1078.004 |
| Shift left | R1, R2, R4, R5, R6, R8, R12, R13 | CM, SA, SC | AIS, CCC, IVS | T1530, T1190, T1133, T1552.001 |
| Identity | R2, R3, R6, R11 | AC, IA | IAM | T1078.004, T1098, T1552.005 |
| Monitor | R7, R9, R10 | CA, CM, SI | LOG, TVM | T1562.008, T1530 |
| Respond | R3, R7 | AU, IR, SI | LOG, SEF | T1562.008, T1070 |

## 5.10 Residual Risk after Controls

Table 5.2 re-scores the register of Chapter 4 assuming the framework is in place. Preventive guardrails mainly reduce *likelihood*, because the risky configuration can no longer be created. Identity controls and segmentation mainly reduce *impact*, because a compromised resource reaches less.

Table 5.2: Residual risk after applying the framework

| ID | Risk | Key controls | Before | After | Residual rating |
| --- | --- | --- | :---: | :---: | --- |
| R1 | Public storage exposure | Account-level Block Public Access, Azure Policy deny, IaC gate | 20 | 5 | Medium |
| R2 | Over-privileged identities | Least privilege, Access Analyzer, IaC rules | 16 | 8 | Medium |
| R3 | Leaked long-lived credentials | OIDC federation, no IAM user keys, secret scanning | 20 | 8 | Medium |
| R4 | Management ports open to the internet | SCP/Azure Policy, Session Manager or Bastion | 16 | 4 | Low |
| R5 | Publicly accessible databases | Guardrail deny, private subnets, IaC gate | 15 | 5 | Medium |
| R6 | SSRF to metadata credentials chain | IMDSv2 by default, scoped roles, attack-path review | 15 | 5 | Medium |
| R7 | Insufficient logging | Organisation trail, log-archive account, SCP | 12 | 4 | Low |
| R8 | Missing encryption or key management | Encryption by default, KMS rotation | 9 | 3 | Low |
| R9 | Configuration drift | Drift detection, change control, exceptions with expiry | 12 | 6 | Medium |
| R10 | Insecure SaaS and PaaS defaults | SaaS posture reviews, asset discovery | 12 | 8 | Medium |
| R11 | MFA not enforced on cloud or SaaS accounts | MFA everywhere, conditional access | 20 | 5 | Medium |
| R12 | Secrets in code and configuration | Secret managers, IaC and repository scanning | 16 | 6 | Medium |
| R13 | Exposed Kubernetes control planes | Private endpoints, authorised ranges, RBAC | 10 | 5 | Medium |

No risk remains critical or high. The highest residual scores (R2, R3 and R10) concern identities and SaaS platforms, where configuration is spread across many systems and is hardest to bring under a single set of guardrails.

## 5.11 Implementation Roadmap

Table 5.3 suggests an order for an enterprise starting from a typical position: several accounts, partial infrastructure as code and no consistent guardrails.

Table 5.3: Suggested 90-day implementation roadmap

| Phase | Timeline | Actions |
| --- | --- | --- |
| Stop the bleeding | Days 1-30 | Enable account-level S3 Block Public Access and Azure public-access policies; find and close public buckets, containers and databases; enforce MFA on all human identities; turn on organisation-wide CloudTrail and activity logs |
| Guardrails | Days 31-60 | Deploy SCPs and Azure Policy deny rules for the critical settings; make IMDSv2 and encryption the default; replace CI user keys with OIDC federation; add IaC scanning to every infrastructure repository with a critical/high gate |
| Continuous assurance | Days 61-90 | Run CSPM and drift detection on all accounts; prioritise findings by attack path; automate remediation for public storage; write the cloud incident playbook and test it |
| Improve | Ongoing | Review exceptions monthly; add organisation-specific rules after each incident or near miss; extend coverage to SaaS platforms and Kubernetes workloads |
