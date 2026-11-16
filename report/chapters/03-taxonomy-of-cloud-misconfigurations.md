# Taxonomy of Cloud Misconfigurations

## 3.1 Why Misconfigurations Happen

A cloud misconfiguration is a setting, chosen or left at its default by the customer, that weakens the security of a resource relative to its purpose. It is rarely the result of a single careless person. The incidents in Chapter 4 show the same organisational causes again and again:

- **Complexity.** A large provider offers hundreds of services, each with many security-relevant settings, and the same idea (for example "make this private") is expressed differently in each service and each provider.
- **Permissive defaults.** Services have often been designed to be easy to start with. Public access, broad network rules or optional encryption were the default in several services until providers changed them, and the change usually applies only to new resources [32].
- **Self-service and speed.** Any engineer with the right permissions can create and change resources in seconds, so the traditional change board is bypassed by design.
- **Temporary exceptions that become permanent.** Ports opened "for a migration", buckets made public "for a partner" and debugging rules "for one day" outlive the reason they were created.
- **Unclear ownership.** Test accounts, proofs of concept and SaaS tenants created outside central IT are seldom inventoried, patched or monitored. The Midnight Blizzard intrusion started in a legacy test tenant [30].
- **Configuration drift.** Even a well-reviewed configuration changes over time through console edits and urgent fixes.

## 3.2 How Exposed Resources Are Found

Attackers do not need to target a particular company to find its mistakes. Internet-wide scanning for open storage, databases and administration ports is cheap and largely automated, and security researchers use the same techniques to find and report exposures, as UpGuard, SOCRadar and SafetyDetectives did in several of the cases in Chapter 4 [23], [25], [26], [27]. In the Capital One case, the attacker used a tool she built to scan for misconfigured AWS accounts and accessed data from around 30 organisations, not only Capital One [22]. Keys and passwords committed to public code repositories are found by automated search in the same way [38]. The practical consequence is that the time between a misconfiguration being introduced and being discovered by someone else can be very short, and "nobody knows it is there" is not a defence.

Figure 3.1 shows the general sequence and, for each stage, the type of control from Chapter 5 that breaks it.

![Figure 3.1: How a misconfiguration becomes a breach, and the control that breaks each stage](figures/fig-3-1-misconfiguration-to-breach.png)

## 3.3 Overview of the Taxonomy

Table 3.1 lists the misconfiguration classes used in this report, with typical examples, the attacker techniques they enable [11], the NIST SP 800-53 controls they violate [8] and the CloudGuard rules that detect them.

Table 3.1: Taxonomy of cloud misconfigurations

| Class | Typical examples | ATT&CK techniques | NIST SP 800-53 | CloudGuard rules |
| --- | --- | --- | --- | --- |
| Storage exposure | Public bucket ACL or policy, public Blob container, missing Block Public Access | T1530 | AC-3, AC-6, SC-7 | CG-S3-001 to 004, CG-AZ-ST-001/002 |
| Identity and access | `*` on `*`, broad S3 read, AdministratorAccess, public role trust, static keys | T1078.004, T1098 | AC-2, AC-6, IA-5 | CG-IAM-001 to 005, CG-AKS-002 |
| Network exposure | SSH/RDP or database ports open to 0.0.0.0/0, public instances | T1133, T1190 | SC-7, AC-17 | CG-NET-001 to 003, CG-AZ-NET-001, CG-EC2-002 |
| Compute and metadata | IMDSv1 allowed on internet-facing instances | T1552.005 | AC-6, SC-7 | CG-EC2-001 |
| Data protection | Unencrypted volumes and databases, TLS below 1.2, plain HTTP, no key rotation | (enables T1530) | SC-8, SC-12, SC-28 | CG-S3-005, CG-EBS-001, CG-RDS-002, CG-KMS-001, CG-AZ-ST-003/004 |
| Logging and monitoring | No or single-region CloudTrail, validation off, logging off, no flow logs | T1562.008, T1070 | AU-2, AU-9, AU-12 | CG-LOG-001 to 004, CG-VPC-001 |
| Secrets | Passwords and tokens in user data or environment variables | T1552.001 | IA-5, SC-28 | CG-EC2-003, CG-LAMBDA-001 |
| Managed databases | Public endpoints, allow-all firewall rules, no backups | T1190, T1485 | SC-7, CP-9 | CG-RDS-001/003, CG-AZ-SQL-001/002 |
| Kubernetes control planes | Public API endpoint without restriction, RBAC disabled | T1133, T1078.004 | SC-7, AC-3 | CG-EKS-001, CG-AKS-001/002 |
| Resilience | No versioning, no purge protection, short backups | T1485, T1490 | CP-9 | CG-S3-006, CG-AZ-KV-001, CG-RDS-003 |
| SaaS and PaaS defaults | Data APIs public by default, accounts without MFA | T1530, T1078.004 | AC-3, IA-2 | (outside IaC; Section 3.13) |
| Drift | Reviewed settings changed later | (any) | CM-3, CM-6 | `cloudguard drift` |

## 3.4 Storage Exposure

Object storage (S3 buckets, Azure Blob containers) is the single most common source of large cloud data leaks, because one setting can expose millions of files at once and the storage address is often guessable from the company or product name. Exposure happens in three ways: an access control list that grants read access to everyone, a bucket policy whose principal is `*` without conditions, or a container access level of `blob` or `container` on Azure. AWS added account-level and bucket-level Block Public Access to override all three, and since April 2023 enables it by default for new buckets [32]. Buckets created before that date, and buckets whose block was switched off for a partner integration, remain exposed until someone checks. In the taxonomy, a missing or partly disabled public access block is reported even when the bucket is currently private, because it removes the safety net that stops the next mistake.

## 3.5 Identity and Access

Identity is the real perimeter in the cloud. The typical identity misconfigurations are policies that allow every action on every resource; policies that allow reading every bucket when a workload needs one prefix; long-lived access keys for IAM users, particularly users with administrator rights; and role trust policies that allow any AWS account (`Principal: "*"`) to assume the role. They rarely cause a breach alone, but they decide its size. The Capital One role could read far more buckets than the firewall needed [21], and a leaked administrator key gives full control of an account. Missing MFA on human accounts is the identity misconfiguration behind the Snowflake customer breaches and the Midnight Blizzard intrusion [29], [30].

## 3.6 Network Exposure

Security groups and network security groups decide which addresses can reach a resource. Opening SSH (22) or RDP (3389) to `0.0.0.0/0` exposes administration services to password guessing and exploitation; opening database and cache ports (3306, 5432, 1433, 27017, 6379, 9200) exposes data stores directly. An "allow all" rule, often created while troubleshooting, opens every port at once. Public IP addresses on instances that do not need to be reachable from the internet add to the exposure, because they bypass the load balancers and firewalls placed in front of an application.

## 3.7 Compute and the Instance Metadata Service

Every cloud virtual machine can query a local metadata service for information about itself, including the temporary credentials of the role attached to it. With the original version (IMDSv1), a simple HTTP GET request returns these credentials. If an application on the instance has a server-side request forgery (SSRF) flaw, an attacker can make the application send that request and return the credentials, then use them from anywhere. This is the widely reported mechanism of the Capital One breach. IMDSv2 requires a session token obtained with a PUT request, which defeats most SSRF attacks [20]. Allowing IMDSv1 on an internet-facing instance is therefore a high-severity misconfiguration even though it looks like a harmless compatibility setting.

## 3.8 Data Protection and Key Management

Encryption at rest protects data if storage media, snapshots or backups are exposed or copied. Common misconfigurations are unencrypted EBS volumes and RDS databases (whose snapshots then carry the data in clear), storage accounts that still accept TLS 1.0 or plain HTTP, and customer-managed keys without automatic rotation. Encryption does not stop an attacker who has valid credentials or a public bucket, because the service decrypts data for any authorised request. That is why the taxonomy treats encryption mainly as a control that limits damage, not one that prevents access.

## 3.9 Logging and Monitoring

Without logs, an organisation cannot tell whether a misconfiguration was exploited, which is the most common answer in public breach statements ("no evidence of access") and often means "no evidence either way". Typical gaps are accounts with no CloudTrail trail, trails that cover only one region (attackers often operate in unused regions), trails without log file validation, trails where logging has been switched off, and VPCs without flow logs. Attackers deliberately disable or alter cloud logs (ATT&CK T1562.008) [11], so logging configuration must itself be protected by guardrails. In India, the CERT-In directions make 180-day log retention a legal requirement [12].

## 3.10 Secrets in Configuration and Code

Passwords, API tokens and access keys written directly into instance user data, function environment variables, IaC files or source code are readable by anyone with read access to that configuration, and they often end up in version control. Toyota disclosed in 2022 that an access key for its T-Connect data server had been published on GitHub for about five years [38]. The safe pattern is to store secrets in a secrets manager and reference them by identifier. The secret scanner must be careful to tell a reference, such as a Secrets Manager ARN, from a secret value, a distinction that CloudGuard initially got wrong (Section 6.7.5).

## 3.11 Managed Databases and Data Platforms

Managed databases add their own exposure settings on top of the network: a `publicly_accessible` flag on RDS, public network access and firewall rules on Azure SQL, and access policies on data warehouses. An Azure SQL firewall rule from 0.0.0.0 to 255.255.255.255 admits every address on the internet. Database misconfigurations also include missing backups and deletion protection, which turn an intrusion or an operator error into permanent data loss. The SBI Quick exposure in Chapter 4 was a database server with no password at all [31].

## 3.12 Kubernetes Control Planes

Managed Kubernetes services (EKS, AKS) expose an API server that controls every workload in the cluster. If that endpoint is reachable from the whole internet, a leaked kubeconfig file or an API server vulnerability can be exploited from anywhere. Disabling Kubernetes role-based access control gives every authenticated user full control. The Tesla incident of 2018, in which an administrative Kubernetes console without a password exposed cloud credentials that were then used for cryptocurrency mining, shows how a container platform's control plane can become the way into the wider cloud account [24]. The NSA and CISA Kubernetes hardening guidance covers these controls in detail [35].

## 3.13 SaaS and PaaS Defaults

Some of the largest exposures in recent years happened in fully managed services where no infrastructure code existed. In 2021, UpGuard found that Microsoft Power Apps portals with OData APIs enabled exposed list data publicly by default unless table permissions were explicitly turned on, revealing about 38 million records across many organisations; Microsoft later changed the default [25]. In 2024, attackers used credentials stolen by infostealer malware to log into Snowflake customer accounts that did not require MFA [29]. Neither the provider's infrastructure nor its software was broken in these cases; the tenant configuration was. These platforms sit outside IaC scanners such as CloudGuard and need their own posture reviews (Section 5.7).

## 3.14 Configuration Drift

Drift is the gap between the configuration that was reviewed and the configuration that is running. It arises from console changes during incidents, scripts run outside the pipeline, provider-side changes to defaults and resources imported into code after the fact. Drift is dangerous because it bypasses the review that the organisation believes is protecting it. Chapter 6 shows four realistic drift changes turning a clean configuration into one with two critical and three high findings.

## 3.15 Toxic Combinations and Attack Paths

The most serious incidents combine several misconfigurations, each of which might be rated medium or high on its own:

- An internet-facing instance, plus IMDSv1, plus an over-privileged role, plus sensitive data in reachable buckets, gives the Capital One path.
- A public bucket, plus sensitive data, plus no access logging, gives a silent leak like Pegasus Airlines or Toyota.
- A static key, plus administrator rights, plus no logging, gives full account takeover without a trace.

Analysing findings one resource at a time misses these combinations, which is why the framework in Chapter 5 prioritises by attack path and CloudGuard includes an attack-path analyser (Section 6.5.3).

## 3.16 Summary

Cloud misconfigurations fall into a small number of recurring classes, and most of them involve settings that are the customer's responsibility in every service model. They are discovered quickly by automated scanning, they are often harmless alone but serious in combination, and they can reappear after review through drift. The next chapter tests this taxonomy against ten real incidents.
