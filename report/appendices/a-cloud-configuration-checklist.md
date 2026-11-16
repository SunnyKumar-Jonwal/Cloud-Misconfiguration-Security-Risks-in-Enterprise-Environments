# Appendix A: Cloud Configuration Security Checklist

This checklist turns the framework of Chapter 5 into questions to ask when a new cloud account, subscription or workload is approved, and at each periodic review. Any item answered "no" should be fixed or recorded as an accepted risk with an owner and an expiry date.

## Governance

- [ ] The account or subscription is part of the organisation's landing zone, with production, non-production and logging separated.
- [ ] Every resource has an owner tag and a data-classification tag.
- [ ] Exceptions to the cloud security standard have an owner, a reason and an expiry date.
- [ ] Test, sandbox and legacy environments meet the same baseline as production, or are isolated from it.
- [ ] SaaS platforms holding enterprise data (data warehouses, low-code platforms) are inventoried and reviewed.

## Guardrails

- [ ] S3 Block Public Access is enabled at account level, and Azure Policy denies public blob access.
- [ ] Service Control Policies or Azure Policy prevent disabling logging and deleting log storage.
- [ ] New instances require IMDSv2 by default.
- [ ] Encryption at rest is enabled by default for block storage and databases.
- [ ] Resources can only be created in approved regions.

## Identity and Access

- [ ] Every human identity, including in test tenants and SaaS platforms, requires MFA.
- [ ] No IAM user access keys exist where federation is possible; CI/CD pipelines use OIDC federation.
- [ ] No policy grants `*` on `*` outside tightly controlled break-glass roles.
- [ ] Workload roles grant only the actions and resources they use, reviewed with access analysis tools.
- [ ] Role trust policies name specific accounts, services or identity providers, never `*`.
- [ ] Application permissions (OAuth consents, service principals) are reviewed regularly.

## Network

- [ ] No security group or NSG allows SSH, RDP or database ports from 0.0.0.0/0.
- [ ] Administration uses Session Manager, Azure Bastion or a VPN, not public ports.
- [ ] Databases have no public endpoint and accept connections only from application tiers.
- [ ] Kubernetes API endpoints are private or restricted to known address ranges.

## Data Protection and Secrets

- [ ] Storage, volumes, databases and backups are encrypted, with key rotation enabled.
- [ ] Storage accepts only HTTPS with TLS 1.2 or higher.
- [ ] No passwords, tokens or keys appear in IaC, user data, environment variables or source code.
- [ ] Code repositories are scanned for secrets, including their history.
- [ ] Versioning, backups and deletion protection are enabled for important data.

## Shift Left

- [ ] All infrastructure changes go through infrastructure as code and a pull request.
- [ ] IaC is scanned in the pull request, and critical and high findings block the merge.
- [ ] Scan results are published as SARIF so that they appear on the changed lines.
- [ ] Custom rules for organisation-specific risks have tests that fail when the rule stops working.

## Monitoring and Response

- [ ] CloudTrail (multi-region, with validation) and the Azure activity log go to a separate log-archive account.
- [ ] Logs are kept for at least 180 days, as required by CERT-In.
- [ ] CSPM or equivalent continuously checks the running configuration.
- [ ] Drift between the approved baseline and the running configuration is detected and reviewed.
- [ ] Findings are prioritised by attack path to sensitive data.
- [ ] Alerts exist for public storage changes, logging changes and new privileged keys.
- [ ] A cloud incident playbook exists and has been tested, including the six-hour CERT-In reporting deadline.
