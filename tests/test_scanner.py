"""Tests for the loader, reporters, CLI and the example estates."""

import json
from pathlib import Path

from cloudguard.cli import main
from cloudguard.engine import load_rules, scan
from cloudguard.loader import load

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "acme-retail"


def test_loader_parses_jsonencode_and_heredoc_policies(tmp_path):
    (tmp_path / "main.tf").write_text('''
resource "aws_iam_policy" "a" {
  policy = jsonencode({ Statement = [{ Effect = "Allow", Action = ["s3:GetObject"], Resource = "*" }] })
}
resource "aws_s3_bucket_policy" "b" {
  bucket = "x"
  policy = <<POLICY
{"Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject"}]}
POLICY
}
''', encoding="utf-8")
    inv = load(tmp_path)
    assert inv.by_address["aws_iam_policy.a"].values["policy"]["Statement"][0]["Action"] == ["s3:GetObject"]
    assert inv.by_address["aws_s3_bucket_policy.b"].values["policy"]["Statement"][0]["Principal"] == "*"


def test_loader_records_line_numbers_and_resolves_references(tmp_path):
    (tmp_path / "main.tf").write_text('''# comment
resource "aws_s3_bucket" "b" {
  bucket = "data"
}

resource "aws_s3_bucket_versioning" "v" {
  bucket = aws_s3_bucket.b.id
}
''', encoding="utf-8")
    inv = load(tmp_path)
    assert inv.by_address["aws_s3_bucket.b"].line == 2
    assert inv.by_address["aws_s3_bucket_versioning.v"].line == 6
    assert inv.resolve(inv.by_address["aws_s3_bucket_versioning.v"].values["bucket"]) is inv.by_address["aws_s3_bucket.b"]


def test_vulnerable_example_finds_every_planted_issue():
    findings = scan(load(EXAMPLES / "vulnerable"), load_rules())
    assert len(findings) == 40
    assert {f.rule.severity for f in findings} == {"critical", "high", "medium", "low"}


def test_hardened_example_is_clean():
    assert scan(load(EXAMPLES / "hardened"), load_rules()) == []


def test_cli_exit_codes(capsys):
    assert main(["scan", str(EXAMPLES / "vulnerable")]) == 1
    assert main(["scan", str(EXAMPLES / "vulnerable"), "--fail-on", "none"]) == 0
    assert main(["scan", str(EXAMPLES / "hardened"), "--fail-on", "low"]) == 0
    assert "No misconfigurations found" in capsys.readouterr().out


def test_sarif_output_is_valid_shape(tmp_path):
    out = tmp_path / "r.sarif"
    main(["scan", str(EXAMPLES / "vulnerable"), "--format", "sarif", "--output", str(out), "--fail-on", "none"])
    sarif = json.loads(out.read_text())
    run = sarif["runs"][0]
    assert sarif["version"] == "2.1.0" and run["tool"]["driver"]["name"] == "CloudGuard"
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    for result in run["results"]:
        assert result["ruleId"] in rule_ids
        assert result["locations"][0]["physicalLocation"]["region"]["startLine"] >= 1
        assert result["level"] in {"error", "warning", "note"}


def test_json_and_html_outputs(tmp_path):
    main(["scan", str(EXAMPLES / "vulnerable"), "--format", "json", "--output", str(tmp_path / "r.json"), "--fail-on", "none"])
    data = json.loads((tmp_path / "r.json").read_text())
    assert data["resources"] == 41 and sum(data["summary"].values()) == len(data["findings"]) == 40
    main(["scan", str(EXAMPLES / "vulnerable"), "--format", "html", "--output", str(tmp_path / "r.html"), "--fail-on", "none"])
    page = (tmp_path / "r.html").read_text()
    assert "CloudGuard" in page and "<script" not in page
