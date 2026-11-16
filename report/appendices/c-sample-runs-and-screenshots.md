# Appendix C: Sample Runs and Screenshots

The screenshots in this appendix were captured from real runs of the code in the project repository with `tools/capture_screenshots.py`, which executes each command, converts its terminal output to an image and captures the HTML report from the same run. Every screenshot can be reproduced by running the command shown at the top of it. The scan of the vulnerable estate, the Capital One attack path, the drift report and the Checkov comparison appear in Chapter 6 as Figures 6.2 to 6.5.

## C.1 Test Suite

All automated tests pass: a "fires" and a "stays silent" test for each rule, and tests for the loader, reporters, attack paths, drift, command-line exit codes and the generated rule catalogue. The same suite runs in the GitHub Actions workflow on every pull request.

![Figure C.1: Test run for CloudGuard and the report tooling](../docs/screenshots/01-pytest.png)

## C.2 Scanning the Hardened Estate

The hardened Acme Retail estate applies each rule's remediation. The scan reports no findings, and with `--fail-on low` the command exits with status 0, so a pipeline would let the change through.

![Figure C.2: CloudGuard scan of the hardened estate](../docs/screenshots/03-scan-hardened.png)

## C.3 All Attack Paths in the Vulnerable Estate

The vulnerable estate contains all four attack-path patterns: the Capital One chain (AP-1), two publicly readable data stores (AP-2), an administrator's static key (AP-3) and a public database behind an open MySQL port (AP-4).

![Figure C.3: Attack paths reported for the vulnerable estate](../docs/screenshots/04-attack-paths-vulnerable.png)

## C.4 Rule Catalogue

`python -m cloudguard rules` lists the 39 rules by severity. The same list, with NIST SP 800-53 and ATT&CK mappings, is in Appendix B.

![Figure C.4: The rule catalogue as listed by the command-line tool](../docs/screenshots/07-rules.png)

## C.5 SARIF Output

The SARIF report contains one result per finding with its rule, severity level and file location, so code-scanning platforms can show it on the changed line of a pull request.

![Figure C.5: SARIF output for the vulnerable estate, with the first result](../docs/screenshots/08-sarif-output.png)

## C.6 HTML Report

The HTML report is a single offline file for security reviewers. It shows the totals, every attack path step by step, the findings by category and, for each finding, the remediation advice and an example Terraform fix.

![Figure C.6: Summary and attack paths in the HTML report](../docs/screenshots/10-html-report-summary.png)
