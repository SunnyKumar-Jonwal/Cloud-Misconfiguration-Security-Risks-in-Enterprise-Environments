# Breach Case Studies and Risk Assessment

## 4.1 Selection and Analysis Method

This chapter tests the taxonomy of Chapter 3 against ten publicly documented incidents from 2017 to 2024. The cases were chosen because the misconfiguration involved is described in regulatory documents, court records, company statements or reliable reporting; together they cover AWS, Azure, Kubernetes and SaaS platforms, and they include one Indian case. Several were discovered and reported by security researchers before any known misuse. They are included because they show what was exposed, and the same exposures are found by attackers using the same techniques.

Each case is described with the same structure: what happened, the misconfiguration, and the lesson. Section 4.12 compares the cases and Section 4.13 applies the findings to a reference enterprise.

## 4.2 Case 1: Verizon Customer Records via a Partner's S3 Bucket (2017)

**What happened.** In June 2017, UpGuard found an Amazon S3 bucket operated by NICE Systems, a vendor handling Verizon's customer service call data. It held records including names, addresses, phone numbers and account PINs. UpGuard estimated up to 14 million customers were affected; Verizon said about 6 million unique customers were involved and that no data had been lost or stolen [23]. UpGuard reported the bucket on 13 June, and it was not secured until 22 June.

**Misconfiguration.** A storage bucket set up by a third party was publicly readable. **Class:** storage exposure, third-party governance.

**Lesson.** Data held by vendors on the enterprise's behalf needs the same configuration standards and monitoring as the enterprise's own accounts, and a reported exposure must be closed within hours, not days.

## 4.3 Case 2: Tesla's Kubernetes Console and Cryptomining (2018)

**What happened.** In February 2018, researchers at RedLock reported that a Kubernetes administration console belonging to Tesla had no password. Inside, they found AWS credentials, which attackers had used to run cryptocurrency-mining software on Tesla's cloud resources. The attackers kept CPU usage low and hid their mining pool behind a content delivery network to avoid detection. The credentials could also have given access to an S3 bucket with vehicle telemetry; Tesla said the impact appeared limited to internally used engineering test cars and that customer privacy and vehicle safety were not compromised [24].

**Misconfiguration.** An unauthenticated container-platform console, with cloud credentials stored where the console could read them. **Classes:** Kubernetes control plane, secrets, identity.

**Lesson.** Management interfaces of container platforms are as sensitive as the cloud console itself, and credentials stored inside a cluster extend its blast radius to the whole cloud account.

## 4.4 Case 3: Capital One (2019)

**What happened.** In 2019, an attacker accessed data on about 106 million people in the United States and Canada held by Capital One on AWS. The widely reported mechanism is that a misconfigured web application firewall running on an EC2 instance could be made to send requests on the attacker's behalf (server-side request forgery). Through it, the attacker queried the instance metadata service and obtained temporary credentials for the instance's role, which had permission to list and read a large number of S3 buckets. In August 2020, the US Office of the Comptroller of the Currency fined Capital One USD 80 million, citing failures in risk assessment before migrating to the cloud [21]. In June 2022, a jury convicted the attacker of wire fraud and computer intrusion. Her tool had scanned for misconfigured AWS accounts, and data was taken from around 30 organisations [22].

**Misconfiguration.** An internet-facing component exploitable for SSRF, the metadata service reachable without a session token (IMDSv1), and an instance role with read access far beyond its purpose. **Classes:** network exposure, compute and metadata, identity, in combination.

**Lesson.** No single setting caused the breach; the chain did. AWS released IMDSv2 in November 2019 specifically to defend against this kind of SSRF attack [20]. Chapter 6 reproduces this chain and shows that fixing any one link breaks it.

## 4.5 Case 4: SBI Quick Text Messages Exposed (2019)

**What happened.** In January 2019, TechCrunch reported that a server in a Mumbai data centre storing data for SBI Quick, the State Bank of India's SMS and missed-call banking service, had been left without a password. It held about two months of messages, including phone numbers, bank balances, recent transactions and partial account numbers; the service sends close to three million messages a day [31]. The server was secured after the bank and India's National Critical Information Infrastructure Protection Centre were alerted.

**Misconfiguration.** A data store reachable from the internet with authentication disabled. **Classes:** managed databases and data stores, network exposure.

**Lesson.** The same exposure occurs in data centres and private clouds as in public clouds. Every internet-reachable data store must require authentication and appear in an inventory that is scanned regularly.

## 4.6 Case 5: Microsoft Power Apps Portals (2021)

**What happened.** In 2021, UpGuard found that Power Apps portals with OData APIs enabled returned list data publicly unless table permissions had been explicitly enabled, because public access was the default for these lists. About 38 million records were exposed across many organisations, including state and city bodies and private companies, with data such as COVID-19 vaccination status and social security numbers [25]. UpGuard reported the issue on 24 June 2021. Microsoft initially closed the report as working by design, and later changed Power Apps portals so that table permissions are enabled by default.

**Misconfiguration.** An insecure default in a low-code SaaS platform, left unchanged by its customers. **Class:** SaaS and PaaS defaults.

**Lesson.** "The provider's default" is not the same as "secure". Platforms used by business teams outside IT need posture reviews, and providers should make the safe setting the default.

## 4.7 Case 6: BlueBleed, Microsoft's Misconfigured Blob Storage (2022)

**What happened.** In September 2022, the threat-intelligence company SOCRadar found a misconfigured Azure Blob Storage endpoint maintained by Microsoft that exposed business data such as invoices, product orders and signed customer documents dating from 2017 to August 2022. SOCRadar estimated 2.4 TB of data relating to more than 65,000 entities in 111 countries; Microsoft confirmed the misconfiguration, secured the storage within hours of being notified and said the scale had been greatly exaggerated [26].

**Misconfiguration.** Publicly accessible Blob storage holding business documents. **Class:** storage exposure.

**Lesson.** Even the cloud provider's own teams make configuration mistakes, so organisation-wide guardrails against public storage matter more than individual diligence.

## 4.8 Case 7: Pegasus Airlines Electronic Flight Bag Data (2022)

**What happened.** In 2022, researchers at SafetyDetectives found an unprotected AWS S3 bucket belonging to Pegasus Airlines that held data from its Electronic Flight Bag system: about 23 million files, around 6.5 TB, including flight charts, navigation material, crew details and, in more than 1.6 million files, crew personal information. The bucket also contained source code with plain-text passwords and secret keys [27]. The researchers found it on 28 February 2022 and contacted the airline on 1 March; securing it took nearly a month.

**Misconfiguration.** A publicly accessible bucket, plus secrets stored in the exposed source code. **Classes:** storage exposure, secrets.

**Lesson.** Operational and safety data can be as sensitive as customer data, and secrets in code turn a data leak into a potential system compromise.

## 4.9 Case 8: Toyota Connected Vehicle Data (2023, with a 2022 key leak)

**What happened.** In May 2023, Toyota disclosed that a cloud environment operated by its subsidiary Toyota Connected had been set to public access without authentication because of human error. As a result, vehicle data of about 2.15 million customers in Japan was exposed for almost ten years (from November 2013 to April 2023), including in-vehicle terminal IDs, chassis numbers, vehicle location and time; reporting also mentioned video from drive recorders. Toyota said it had found no evidence of misuse [28]. Separately, in October 2022, Toyota had disclosed that an access key to its T-Connect data server had been published on GitHub for about five years, potentially exposing data of about 296,000 users [38].

**Misconfiguration.** A cloud data store configured for public access, undetected for a decade; and a credential committed to a public repository. **Classes:** storage exposure, secrets, logging and monitoring.

**Lesson.** A misconfiguration that is never detected can last for years. Continuous posture monitoring and secret scanning would have shortened both exposures from years to days.

## 4.10 Case 9: Snowflake Customer Accounts (2024)

**What happened.** In 2024, a financially motivated group tracked by Mandiant as UNC5537 logged into Snowflake customer accounts using credentials stolen by infostealer malware, some dating back to 2020, and stole and extorted data. Mandiant found no breach of Snowflake's own platform: access was achieved with valid credentials on accounts that did not require MFA and whose passwords had not been rotated, sometimes for years [29]. Around 165 organisations were notified as potentially exposed. Companies that later disclosed related data theft included Ticketmaster and AT&T.

**Misconfiguration.** Customer accounts on a cloud data platform without MFA and without network access restrictions, and credentials never rotated. **Classes:** identity, SaaS and PaaS defaults.

**Lesson.** MFA and network policies on SaaS data platforms are configuration choices the customer must enforce. A platform holding an enterprise's most valuable data must be governed like its own cloud accounts.

## 4.11 Case 10: Midnight Blizzard and a Legacy Test Tenant (2024)

**What happened.** In January 2024, Microsoft disclosed that the state-sponsored group Midnight Blizzard had used a password-spray attack, at a deliberately low rate to avoid lockouts, to compromise a legacy, non-production test tenant account that did not have MFA. From there, the attackers used a legacy test OAuth application that had elevated access to Microsoft's corporate environment, created further malicious OAuth applications and granted themselves access to Exchange Online mailboxes, including those of senior leadership, security and legal staff [30]. Microsoft said that if the same legacy tenant were deployed today, mandatory policies would require MFA.

**Misconfiguration.** A forgotten test tenant with weaker settings than production, and an application in it with excessive permissions into the production environment. **Classes:** identity, ownership and governance.

**Lesson.** Test and legacy environments must meet the same baseline as production, or be isolated from it. Application permissions (OAuth consents, service principals) are part of the identity attack surface.

## 4.12 Cross-Case Analysis

Table 4.1 maps each case to the misconfiguration classes of Chapter 3.

Table 4.1: Misconfiguration classes in each case

| Case | Storage | Identity | Network | Compute/IMDS | Secrets | Databases | Kubernetes | SaaS defaults | Monitoring gap |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 Verizon/NICE | Yes | | | | | | | | Yes |
| 2 Tesla | | Yes | Yes | | Yes | | Yes | | Yes |
| 3 Capital One | Yes | Yes | Yes | Yes | | | | | |
| 4 SBI Quick | | | Yes | | | Yes | | | Yes |
| 5 Power Apps | Yes | | | | | | | Yes | |
| 6 BlueBleed | Yes | | | | | | | | |
| 7 Pegasus | Yes | | | | Yes | | | | Yes |
| 8 Toyota | Yes | | | | Yes | | | | Yes |
| 9 Snowflake | | Yes | | | | Yes | | Yes | |
| 10 Midnight Blizzard | | Yes | | | | | | Yes | |

Four patterns stand out.

1. **Storage and identity dominate.** Six cases involved publicly exposed storage and four involved identity weaknesses. These are also the two classes that are the customer's responsibility in every service model (Section 2.2).
2. **Long exposure is common.** Several exposures lasted for months or years (Toyota for almost ten years, the T-Connect key for five, Snowflake credentials stolen as early as 2020). Prevention matters, but detection is what limits how long a mistake stays open.
3. **The largest breach was a chain.** Capital One combined four individually moderate weaknesses. Rules that look at one resource at a time would have produced several medium and high findings, but no single critical one (Section 6.7.2).
4. **SaaS and test environments are blind spots.** Three cases happened in SaaS platforms or forgotten tenants, outside the infrastructure code that most scanning focuses on.

Table 4.2 lists, for each case, the control from Chapter 5 that would most directly have prevented it and whether a CloudGuard rule or path covers the pattern.

Table 4.2: Preventing controls and CloudGuard coverage

| Case | Most effective control | CloudGuard coverage |
| --- | --- | --- |
| 1 Verizon/NICE | Account-level Block Public Access; vendor configuration standards | CG-S3-001 to 004, AP-2 |
| 2 Tesla | Authenticated, private control planes; no long-lived keys in clusters | CG-EKS-001, CG-AKS-001/002, CG-IAM-003 |
| 3 Capital One | IMDSv2, least-privilege roles, private instances | CG-EC2-001, CG-IAM-002, CG-EC2-002, AP-1 |
| 4 SBI Quick | Authentication on every data store; network restrictions | CG-NET-003, CG-RDS-001, AP-4 (for AWS-hosted equivalents) |
| 5 Power Apps | SaaS posture review; secure defaults | Not covered (outside IaC) |
| 6 BlueBleed | Azure Policy denying public blob access | CG-AZ-ST-001/002, AP-2 |
| 7 Pegasus | Block Public Access; secrets manager | CG-S3-001 to 004, CG-EC2-003, CG-LAMBDA-001 |
| 8 Toyota | Continuous posture monitoring; secret scanning | Storage rules; secrets rules (configuration only, not repository history) |
| 9 Snowflake | MFA and network policies on SaaS accounts | Not covered (outside IaC) |
| 10 Midnight Blizzard | Same baseline for test tenants; review application permissions | Not covered (identity tenant settings) |

Seven of the ten patterns can be detected in infrastructure code; three cannot, which is why the framework in Chapter 5 also includes runtime monitoring and SaaS reviews.

## 4.13 Risk Assessment of a Reference Enterprise

### 4.13.1 Reference Enterprise

The risk assessment uses a hypothetical Indian retail and e-commerce company with about 8,000 employees, running its online store and analytics on AWS and its finance applications on Azure. It has around 30 cloud accounts and subscriptions, uses Terraform for most new infrastructure, has some resources created by hand in earlier years, and uses SaaS platforms for analytics and low-code business apps. This is the company modelled by the "Acme Retail" Terraform estate used in Chapter 6.

### 4.13.2 Scoring Method

Each risk was scored for likelihood and impact on the five-point scales in Table 4.3. The score is their product. Scores of 20 and above are *critical*, 10 to 19 *high*, 5 to 9 *medium* and below 5 *low*.

Table 4.3: Likelihood and impact scales

| Score | Likelihood | Impact |
| --- | --- | --- |
| 1 | Rare: no known exposure or technique | Negligible: no data or service effect |
| 2 | Unlikely: needs insider access or rare conditions | Minor: limited internal data, quick recovery |
| 3 | Possible: known technique, some exposure | Moderate: confidential data of one function |
| 4 | Likely: automated scanning finds it, wide exposure | Major: customer data, regulatory reporting, outage |
| 5 | Almost certain: already seen in comparable estates | Severe: large-scale breach, regulatory penalty, loss of trust |

### 4.13.3 Risk Register

Table 4.4 gives the resulting register. Owners are the roles that would normally be accountable in an enterprise of this kind.

Table 4.4: Cloud misconfiguration risk register for the reference enterprise (before controls)

| ID | Risk | L | I | Score | Rating | Owner |
| --- | --- | :---: | :---: | :---: | --- | --- |
| R1 | Customer or business data exposed through public storage | 4 | 5 | 20 | Critical | Cloud platform lead |
| R2 | Over-privileged identities and roles | 4 | 4 | 16 | High | IAM lead |
| R3 | Long-lived access keys leaked through code, CI or laptops | 4 | 5 | 20 | Critical | DevOps lead |
| R4 | SSH, RDP or other management ports open to the internet | 4 | 4 | 16 | High | Network security lead |
| R5 | Databases reachable from the internet | 3 | 5 | 15 | High | Database owner |
| R6 | SSRF leading to instance credentials through IMDSv1 | 3 | 5 | 15 | High | Application security lead |
| R7 | Insufficient or disabled logging | 4 | 3 | 12 | High | SOC manager |
| R8 | Missing encryption or key management | 3 | 3 | 9 | Medium | Data protection officer |
| R9 | Configuration drift from unreviewed changes | 4 | 3 | 12 | High | Change manager |
| R10 | Insecure defaults in SaaS and PaaS platforms | 3 | 4 | 12 | High | Business application owners |
| R11 | MFA not enforced on cloud or SaaS accounts | 4 | 5 | 20 | Critical | IAM lead |
| R12 | Secrets in code and configuration | 4 | 4 | 16 | High | DevOps lead |
| R13 | Kubernetes control planes exposed or without RBAC | 2 | 5 | 10 | High | Platform engineering lead |

### 4.13.4 Heat Map

Figure 4.1 plots the register on a likelihood and impact grid.

![Figure 4.1: Risk heat map of the reference enterprise before controls](figures/fig-4-1-risk-heat-map.png)

Three risks are critical: public storage (R1), leaked long-lived keys (R3) and missing MFA (R11). All three match the most frequent patterns in the case studies. Nine more are high. The concentration in the upper right of the grid reflects the main finding of this chapter: in the cloud, a configuration mistake is both likely to be found and likely to be serious when it is.

## 4.14 Summary

The ten cases confirm the taxonomy: every incident maps to one or more of its classes, storage and identity dominate, and the largest breach was a chain of moderate weaknesses. Seven of the ten patterns are visible in infrastructure code, while three lie in SaaS and identity tenants that need runtime controls. The risk register turns these observations into priorities for a reference enterprise, and Chapter 5 proposes the controls that bring them down.
