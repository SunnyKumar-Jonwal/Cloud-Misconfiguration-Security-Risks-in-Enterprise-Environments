# Conclusion and Future Scope

## 7.1 Conclusion

This project set out to understand why cloud misconfiguration causes so many enterprise breaches and how it can be prevented and detected systematically. Its central conclusion is that cloud breaches caused by misconfiguration are rarely failures of technology. They are failures of configuration management at scale. The cloud providers' platforms did what they were configured to do in every one of the ten cases studied. What failed was the customer's control over thousands of settings, changed by many people, through many tools, over many years.

Chapter 2 showed that data, identities and access remain the customer's responsibility in every service model. Chapter 3 organised misconfigurations into a taxonomy of twelve classes and showed how quickly exposed resources are found by automated scanning. Chapter 4 tested the taxonomy against ten incidents, from the Verizon/NICE bucket in 2017 to the Snowflake and Midnight Blizzard intrusions in 2024, and found that storage exposure and identity weaknesses dominate, that exposures often last for years, and that the largest breach, Capital One, was a chain of individually moderate weaknesses. The risk assessment of a reference Indian enterprise placed public storage, leaked long-lived keys and missing MFA at the top.

Chapter 5 proposed a five-stage framework (govern, guardrail, shift left, monitor, respond) built on identity and data classification, and Chapter 6 built and evaluated CloudGuard to test its central technical ideas. The scanner found every misconfiguration planted in the vulnerable example estate and nothing in the hardened one, traced the Capital One chain end to end, and attributed every new finding in a drifted configuration to the change that caused it. The comparison with Checkov was the most instructive result. The established scanner caught 35 of the 40 issues and covered much more ground overall, but missed four real problems that the smaller rule set caught, one of them because a provider had renamed an attribute. No single scanner is enough, and every rule needs tests that tell its owners when it stops working.

## 7.2 Key Findings

1. **Configuration, not platforms, is the weak point.** In all ten cases, the provider's platform worked as configured; the customer's configuration exposed the data.
2. **Storage and identity dominate.** Six of the ten cases involved publicly exposed storage and four involved identity weaknesses, the two areas that stay with the customer in every service model.
3. **Exposures last a long time when nobody is looking.** Toyota's data was exposed for almost ten years and its T-Connect key for five. Detection limits the damage as much as prevention does.
4. **The worst breaches are chains.** The Capital One configuration rated "high" at worst finding by finding, but critical as a chain; attack-path analysis is needed to see it.
5. **Drift undoes reviews.** Four realistic unreviewed changes turned a clean configuration into one with two critical and three high findings.
6. **SaaS and test tenants are blind spots.** Three of the ten cases fall outside infrastructure code and need runtime and tenant-level controls.
7. **Scanners miss things silently.** Even a mature scanner passed four real issues, including one caused by a provider schema change. Layered tools and tested rules are necessary.

## 7.3 Recommendations for Enterprises

In rough order of value for effort:

1. Enable S3 Block Public Access at account level and deny public blob access with Azure Policy, then find and close every existing public data store.
2. Enforce MFA on every human identity, including test tenants and SaaS data platforms.
3. Remove IAM user access keys; use roles, and OIDC federation for CI/CD.
4. Require IMDSv2 on all instances and review every role that an internet-facing workload can use.
5. Send logs from every account and region to a separate log-archive account, and keep them for at least 180 days.
6. Scan all infrastructure code in pull requests, block critical and high findings, and show results as SARIF annotations.
7. Run continuous posture monitoring and drift detection on the live environment, including resources created outside code.
8. Prioritise remediation by attack path to sensitive data, using classification tags on every data store.
9. Give every exception an owner and an expiry date, and review exceptions monthly.
10. Add an organisation-specific rule, with tests, after every incident or near miss, and keep a broad community scanner alongside it.

## 7.4 Contributions of the Project

- A taxonomy of twelve misconfiguration classes mapped to MITRE ATT&CK, NIST SP 800-53 and detection rules (Chapter 3)
- A comparative analysis of ten incidents with a common method, including an Indian case, and a risk register for a reference Indian enterprise (Chapter 4)
- A lifecycle framework with a standards mapping, residual risk scores and a 90-day roadmap (Chapter 5)
- CloudGuard, an open, tested policy-as-code scanner for AWS and Azure Terraform with attack-path analysis, drift detection and SARIF output, plus a reproducible comparison with Checkov (Chapter 6)

## 7.5 Limitations

The incident analysis depends on public sources whose detail varies and which are sometimes disputed. The risk scores are expert judgements for a hypothetical enterprise. CloudGuard reads Terraform only, has 39 rules and four attack-path patterns, and was evaluated on purpose-built configurations written by its author; the comparison with Checkov uses one version and four small configurations. These limits do not change the main conclusions, which rest on consistent patterns across all sources, but they bound how precisely the numbers should be read.

## 7.6 Future Scope

- **Live-environment scanning.** Extend CloudGuard to read configuration through provider APIs or exported state, so that console-created resources and provider defaults are covered.
- **Richer attack paths.** Model network routing, resource policies on other services and Azure role assignments, and compute paths as graphs, as CNAPP platforms do.
- **Terraform plan evaluation.** Analyse `terraform plan` output so that variables, modules and `count`/`for_each` expansions are resolved before rules are evaluated.
- **SaaS posture.** Add checks for SaaS platforms such as data warehouses and low-code portals, where three of the ten incidents occurred.
- **Automatic fixes.** Turn each rule's example fix into a suggested change on the pull request.
- **Larger evaluation.** Run CloudGuard and other scanners on a large corpus of open-source Terraform to measure precision and recall on real-world code, and track how rules decay as provider schemas change.

Cloud platforms will keep adding services and settings faster than people can review them. The organisations that avoid the next Capital One or Toyota will be the ones that make secure settings the default, check every change automatically, keep watching what is actually running, and treat each incident, their own or someone else's, as a new rule.
