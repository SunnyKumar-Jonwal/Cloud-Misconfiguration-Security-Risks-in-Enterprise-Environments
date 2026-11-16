# Appendix D: Running the Project Locally

This appendix shows, step by step, how to set up and run the project on a local machine. Every screenshot is a real run of the step, made in a fresh clone of the repository with a new Python virtual environment, by `tools/capture_setup_guide.py`. In the clone command, `<username>` stands for the GitHub account or organisation that hosts the repository. The same guide, with copyable commands, is in `docs/LOCAL-SETUP.md`.

## D.1 Prerequisites and Getting the Code

Python 3.10 or newer and Git are required. LibreOffice is needed only to build the PDF version of the report.

![Figure D.1: Step 1, checking the installed versions of Python, Git and LibreOffice](../docs/setup-screenshots/01-check-prerequisites.png)

![Figure D.2: Step 2, cloning the repository](../docs/setup-screenshots/02-clone-repository.png)

![Figure D.3: Step 3, opening the project folder](../docs/setup-screenshots/03-open-project-folder.png)

## D.2 Setting Up the Environment

On Windows, the virtual environment is activated with `.venv\Scripts\Activate.ps1`. CloudGuard needs only python-hcl2 and PyYAML; python-docx and pypdf are used to build the report.

![Figure D.4: Step 4, creating and activating a virtual environment](../docs/setup-screenshots/04-create-virtual-environment.png)

![Figure D.5: Step 5, installing the dependencies](../docs/setup-screenshots/05-install-dependencies.png)

![Figure D.6: Step 6, running the test suite](../docs/setup-screenshots/06-run-tests.png)

## D.3 Running CloudGuard

Step 7 scans the vulnerable estate, here limited to critical findings for readability, and Step 8 shows the hardened estate passing. Steps 9 and 10 run the attack-path analysis and the drift comparison.

![Figure D.7: Step 7, scanning the vulnerable estate (critical findings only)](../docs/setup-screenshots/07-scan-the-vulnerable-estate.png)

![Figure D.8: Step 8, scanning the hardened estate](../docs/setup-screenshots/08-scan-the-hardened-estate.png)

![Figure D.9: Step 9, finding the attack path in the Capital One replay](../docs/setup-screenshots/09-find-attack-paths.png)

![Figure D.10: Step 10, detecting drift against the approved baseline](../docs/setup-screenshots/10-detect-drift.png)

## D.4 Reports

Step 11 writes the HTML and SARIF reports, and Step 12 shows the HTML report opened in a browser.

![Figure D.11: Step 11, creating the HTML and SARIF reports](../docs/setup-screenshots/11-create-html-and-sarif-reports.png)

![Figure D.12: Step 12, the HTML report opened in a browser](../docs/setup-screenshots/12-open-html-report-in-browser.png)

## D.5 Building the Project Report

After filling in the personal details in `report/metadata.yaml`, the report is built as a Word document and a PDF. The first page of the PDF built in this run shows the placeholders that `metadata.yaml` replaces.

![Figure D.13: Step 13, building the report as DOCX and PDF](../docs/setup-screenshots/13-build-the-report.png)

![Figure D.14: Step 14, the first page of the built report](../docs/setup-screenshots/14-open-the-built-report.png)
