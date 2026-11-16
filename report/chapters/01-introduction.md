# Introduction

## 1.1 Background

Public cloud platforms have changed how enterprises build and run IT. Instead of buying servers and waiting weeks for a network change, a team can create a database, a storage bucket or an entire Kubernetes cluster in minutes, through a web console, an API call or a few lines of code. Large enterprises now run thousands of such resources across several cloud providers, managed by dozens of teams.

This speed has a price. Every cloud resource comes with settings that decide who can reach it, who can use it and what happens to its data: whether a storage bucket can be read by anyone on the internet, whether a database has a public address, whether an identity can do everything in an account, whether activity is logged at all. These settings belong to the customer, not the cloud provider, and a single wrong value can expose millions of records. Gartner predicted that through 2025, 99% of cloud security failures would be the customer's fault [1], and the Cloud Security Alliance's survey of industry experts places identity, access and configuration problems among the most serious cloud threats [3].

The breach record confirms this. In 2019, a misconfigured web application firewall at Capital One allowed an attacker to steal temporary cloud credentials and copy the data of about 106 million people, leading to an USD 80 million penalty from a US regulator [21]. Storage left open to the internet exposed customer records at Verizon's partner NICE Systems [23], flight data and crew details at Pegasus Airlines [27] and vehicle location data of 2.15 million Toyota customers for almost a decade [28]. In India, a server used by the State Bank of India's SBI Quick service was left without a password, exposing balances and transaction messages [31]. These incidents were not the result of sophisticated exploits against the cloud platforms. In each case, the platform did what it was configured to do. The average cost of a data breach was USD 4.44 million in 2025 [2], and misconfiguration is one of the most avoidable ways to incur it.

## 1.2 Problem Statement

Cloud configuration is now code, data and policy at the same time. It is spread across infrastructure-as-code repositories, consoles, command-line scripts and the default settings of hundreds of services, and it changes continuously. Traditional security reviews, done once before go-live, cannot keep up. Individual settings that look acceptable on their own can combine into a path from the internet to sensitive data, and a configuration that was secure when reviewed can drift into an insecure one through a single emergency change. The problem this project addresses is therefore:

> *Which cloud misconfigurations create the greatest risk for enterprises, how have they led to real breaches, and how can they be detected and prevented systematically, before deployment and after it, in a way that development teams can adopt?*

## 1.3 Objectives

1. To explain the shared responsibility model and how cloud configuration is managed in enterprises, and to identify which settings are always the customer's responsibility.
2. To develop a taxonomy of cloud misconfigurations covering storage, identity, network, compute, data protection, logging, secrets, managed databases and Kubernetes, mapped to MITRE ATT&CK and NIST SP 800-53.
3. To analyse ten publicly documented incidents from 2017 to 2024 with a common method and to identify their root causes.
4. To assess the misconfiguration risks of a reference enterprise using a likelihood and impact model.
5. To propose a lifecycle framework of preventive and detective controls aligned with recognised standards.
6. To design, implement and evaluate CloudGuard, a policy-as-code scanner for Terraform that detects misconfigurations, attack paths and drift, and to compare it with an established open-source scanner.

## 1.4 Scope and Limitations

The study covers Infrastructure as a Service and Platform as a Service on Amazon Web Services (AWS) and Microsoft Azure, which are widely used by Indian and global enterprises, together with SaaS platforms where their configuration caused incidents. It concentrates on configuration chosen by the customer, not on vulnerabilities in the providers' own software. The prototype analyses Terraform, the most widely used multi-cloud infrastructure-as-code tool [15], and does not connect to live cloud accounts.

The incident analysis relies on public reports, regulatory documents and court records, which differ in detail and are sometimes disputed by the organisations involved. The prototype's evaluation uses purpose-built example configurations and one comparison tool, so it shows how the approach behaves rather than establishing its accuracy on real-world code at scale.

## 1.5 Methodology

1. **Literature and standards review.** Provider documentation on shared responsibility [5], [6], the CIS Benchmarks [7], NIST SP 800-53 [8], ISO/IEC 27017 [9], the CSA Cloud Controls Matrix [10] and Top Threats [3], MITRE ATT&CK for cloud [11] and research on security problems in infrastructure-as-code scripts [16], [17].
2. **Taxonomy.** Misconfigurations were grouped by the resource and control they affect, and each class was mapped to attacker techniques and to controls.
3. **Case study analysis.** Ten incidents were analysed using a common template: context, what was misconfigured, how it was found or exploited, impact, root cause and lesson.
4. **Risk assessment.** The misconfiguration classes were scored for a reference enterprise to produce a risk register and heat map.
5. **Design, implementation and evaluation.** CloudGuard was built and tested with automated tests, four example configurations, attack-path and drift scenarios, and a comparison with Checkov [18].

## 1.6 Organisation of the Report

Chapter 2 explains cloud service models, the shared responsibility model, how configuration is managed, the security tooling landscape and the relevant standards and research. Chapter 3 presents the taxonomy of misconfigurations and how they are exploited. Chapter 4 analyses the ten incidents and assesses risk for a reference enterprise. Chapter 5 proposes the prevention and detection framework. Chapter 6 describes the design, implementation and results of CloudGuard. Chapter 7 concludes with recommendations and future work. The appendices contain a configuration security checklist, the CloudGuard rule catalogue, screenshots of sample runs and a guide to running the project locally.
