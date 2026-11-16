# Cloud Security Background and Literature Review

## 2.1 Cloud Service and Deployment Models

NIST defines cloud computing as a model for convenient, on-demand network access to a shared pool of configurable computing resources that can be rapidly provisioned and released with minimal management effort [4]. Its definition names five essential characteristics (on-demand self-service, broad network access, resource pooling, rapid elasticity and measured service) and three service models:

- **Infrastructure as a Service (IaaS):** the customer rents virtual machines, storage and networks, and manages the operating system and everything above it. Amazon EC2 and Azure Virtual Machines are examples.
- **Platform as a Service (PaaS):** the provider runs the operating system and runtime, and the customer deploys code or data into managed services such as Amazon RDS, Azure SQL Database or a managed Kubernetes control plane.
- **Software as a Service (SaaS):** the provider runs the whole application, and the customer configures users, sharing and integrations. Microsoft 365, Salesforce, Power Apps and Snowflake are examples.

The key phrase in the NIST definition is "configurable computing resources". Self-service means that anyone with the right permissions can create and reconfigure resources without a ticket or a change board, which is what makes the cloud fast and also what makes it easy to misconfigure.

## 2.2 The Shared Responsibility Model

Cloud providers describe security as a shared responsibility: the provider secures the cloud itself (data centres, hardware and the virtualisation layer), and the customer secures what it puts in the cloud and how it configures it [5], [6]. Figure 2.1 shows how the split changes across service models.

![Figure 2.1: The shared responsibility model across on-premises, IaaS, PaaS and SaaS](figures/fig-2-1-shared-responsibility.png)

Two observations matter for this report. First, the provider takes over more of the lower layers as the model moves from IaaS to SaaS, but **data, identities and access are the customer's responsibility in every model**. A SaaS product cannot decide for the customer who should see a list of records, which is why the Power Apps and Snowflake incidents in Chapter 4 happened in fully managed services. Second, the boundary is often misunderstood. Teams assume that a managed service is secure "by default", while many services have historically shipped with permissive defaults to make them easy to adopt. Table 2.1 lists examples of settings that remain the customer's job.

Table 2.1: Examples of security settings that remain the customer's responsibility

| Area | AWS example | Azure example |
| --- | --- | --- |
| Data exposure | S3 bucket policy and Block Public Access | Blob container access level |
| Identity | IAM policies, role trust, access keys, MFA | Entra ID roles, conditional access, MFA |
| Network | Security groups, public IP addresses | Network security groups, public network access |
| Compute | Instance metadata service version (IMDSv1 or IMDSv2) | VM extensions and managed identities |
| Data protection | KMS key use and rotation, RDS encryption | Key Vault purge protection, TLS minimum version |
| Logging | CloudTrail trails, VPC flow logs | Activity log and diagnostic settings |
| Kubernetes | EKS endpoint access | AKS authorised IP ranges and RBAC |

## 2.3 How Cloud Configuration Is Managed in Enterprises

Enterprises configure cloud resources in four main ways, often at the same time:

1. **Web consoles**, which are convenient for exploration and emergencies but leave no reviewable record of intent.
2. **Command-line tools and scripts**, which can be repeated but are rarely reviewed.
3. **Infrastructure as code (IaC)**, such as Terraform, AWS CloudFormation, Azure Bicep or Pulumi. Resources are declared in text files, reviewed in pull requests and applied by a pipeline [15]. Terraform's provider model lets one language describe AWS, Azure and hundreds of other services.
4. **Platform-level policies**, such as AWS Service Control Policies [33] and Azure Policy [34], which apply to every resource in an organisation whoever creates it.

IaC is now the main way large enterprises manage cloud infrastructure, which turns configuration into code and lets familiar software practices (review, testing, static analysis) be applied to it. It also means that a mistake in a reusable module can be copied into hundreds of resources. Rahman et al. studied this directly: in a study of Puppet scripts they identified seven recurring "security smells", including hard-coded secrets, admin by default and invalid IP address bindings, and found them widely spread across open-source repositories [16]. A replication study found similar security smells in Ansible and Chef scripts, showing that the problem is not specific to one tool [17].

## 2.4 The Cloud Security Tooling Landscape

A range of tool categories has grown up around cloud configuration. Table 2.2 summarises them.

Table 2.2: Categories of cloud security tooling

| Category | What it checks | When it runs | Examples of approach |
| --- | --- | --- | --- |
| IaC scanning | Terraform, CloudFormation, Bicep and Kubernetes files | Before deployment, in the pull request | Checkov [18], policy engines such as Open Policy Agent [19] |
| Cloud Security Posture Management (CSPM) | Live configuration through provider APIs | Continuously, after deployment | Provider-native posture services and commercial CSPM |
| Cloud Infrastructure Entitlement Management (CIEM) | Effective permissions of identities | Continuously | Unused and excessive permission analysis |
| Cloud Workload Protection (CWPP) | Vulnerabilities and behaviour of workloads | At build time and at runtime | Image scanning, runtime agents |
| Cloud-Native Application Protection Platform (CNAPP) | A combination of the above, with correlation | Across the lifecycle | Attack-path or "toxic combination" analysis |

Two trends are visible. The first is the "shift left" of configuration checks into the development pipeline, so that problems are caught when they are cheapest to fix. The second is correlation: modern platforms try to link individual findings into attack paths, because a list of thousands of findings without priorities is of little use to an operations team. CloudGuard, described in Chapter 6, explores both ideas in a small, transparent prototype.

## 2.5 Standards and Frameworks

- **CIS Benchmarks** give prescriptive, consensus-based configuration recommendations for AWS, Azure, Kubernetes and many other platforms, and are the most common baseline for posture tools [7].
- **NIST SP 800-53 Rev. 5** is a catalogue of security and privacy controls; families such as AC (Access Control), SC (System and Communications Protection), AU (Audit and Accountability) and CM (Configuration Management) map directly to cloud settings [8]. **NIST SP 800-210** gives access control guidance specifically for cloud systems [14], and **NIST SP 800-207** describes zero trust architecture [36].
- **ISO/IEC 27017** extends ISO/IEC 27002 with controls for cloud service customers and providers, including the division of responsibilities between them [9].
- **The CSA Cloud Controls Matrix (CCM)** is a cloud-specific control framework organised in domains such as Identity and Access Management (IAM), Infrastructure and Virtualization Security (IVS) and Logging and Monitoring (LOG) [10]. The CSA's **Top Threats to Cloud Computing** report is based on a survey of industry experts; its 2022 edition highlighted threats that are under the customer's control, such as identity and access management and configuration [3].
- **MITRE ATT&CK** includes a cloud matrix that catalogues adversary techniques such as *Data from Cloud Storage* (T1530), *Unsecured Credentials: Cloud Instance Metadata API* (T1552.005) and *Impair Defenses: Disable or Modify Cloud Logs* (T1562.008) [11].
- **The NSA and CISA** have published joint guidance on the top ten cloud security mitigation strategies [37] and on Kubernetes hardening [35].
- **Indian regulation.** The CERT-In directions of April 2022 require specified cyber incidents to be reported within six hours and logs of ICT systems to be kept for 180 days [12]. The Digital Personal Data Protection Act, 2023 governs personal data, including data stored in the cloud [13].

## 2.6 Related Work

Research on cloud misconfiguration falls into three strands. The first studies security problems in IaC code, as in the work of Rahman et al. on security smells [16], [17], which shows that the same mistakes recur across projects and can be detected statically. The second is practitioner research by security firms and researchers who scan the internet for exposed storage, databases and SaaS portals, which produced several of the disclosures analysed in Chapter 4 (UpGuard, SOCRadar and SafetyDetectives among them) [23], [25], [26], [27]. The third is the large body of provider and community guidance, such as the AWS documentation on IMDSv2 written after SSRF-based credential theft became a known attack [20] and the default changes to S3 in 2023 [32].

## 2.7 Research Gap

Three gaps motivate this project. First, incident write-ups, standards and tool documentation are rarely brought together: the case studies describe what went wrong, the standards describe what should be done, but few sources trace a breach back to a specific setting and forward to the control that would have stopped it. Second, most IaC checks look at one resource at a time, while breaches such as Capital One combined several individually moderate weaknesses across resources. Third, published comparisons of IaC scanners are scarce, and the ways scanners can silently miss issues, for example when a provider renames an attribute, are seldom discussed. Chapters 3 and 4 address the first gap, and CloudGuard and its comparison with Checkov in Chapter 6 address the second and third.
