"""Tests for attack-path analysis and drift detection."""

from pathlib import Path

from cloudguard.attack_paths import find_paths
from cloudguard.cli import main
from cloudguard.drift import compare, explain
from cloudguard.engine import load_rules
from cloudguard.loader import load

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def ids(paths):
    return sorted(p.id for p in paths)


def test_vulnerable_estate_has_all_four_path_types():
    assert ids(find_paths(load(EXAMPLES / "acme-retail" / "vulnerable"))) == ["AP-1", "AP-2", "AP-2", "AP-3", "AP-4"]


def test_hardened_estate_has_no_paths():
    assert find_paths(load(EXAMPLES / "acme-retail" / "hardened")) == []


def test_capital_one_replay_reaches_only_sensitive_buckets():
    (path,) = find_paths(load(EXAMPLES / "capital-one-replay"))
    assert path.id == "AP-1" and path.severity == "critical"
    last = path.steps[-1].description
    assert "credit-applications" in last and "card-statements" in last and "web-assets" not in last
    assert [s.technique for s in path.steps] == ["T1190", "T1552.005", "T1078.004", "T1530", "T1530"]


def test_capital_one_path_breaks_when_any_link_is_fixed(tmp_path):
    source = (EXAMPLES / "capital-one-replay" / "main.tf").read_text()
    fixes = {
        "imdsv2": ('http_tokens = "optional"', 'http_tokens = "required"'),
        "private": ("associate_public_ip_address = true", "associate_public_ip_address = false"),
        "scoped role": ('Resource = "*" }]', 'Resource = "arn:aws:s3:::example-bank-web-assets/*" }]'),
    }
    for name, (old, new) in fixes.items():
        assert old in source, name
        case = tmp_path / name.replace(" ", "-")
        case.mkdir()
        (case / "main.tf").write_text(source.replace(old, new))
        assert find_paths(load(case)) == [], f"path should break when fixing: {name}"


def test_drift_traces_each_new_finding_to_the_change_that_caused_it():
    report = compare(load(EXAMPLES / "acme-retail" / "hardened"), load(EXAMPLES / "acme-retail" / "drifted"), load_rules())
    assert report.added == [] and report.removed == []
    assert len(report.changed) == 5 and len(report.new_findings) == 5 and report.resolved_findings == []
    causes = explain(report)
    assert causes["CG-EC2-001 aws_instance.web"] == ["metadata_options.0.http_tokens"]
    assert causes["CG-LOG-004 aws_cloudtrail.main"] == ["enable_logging"]


def test_drift_of_identical_directories_is_empty():
    report = compare(load(EXAMPLES / "acme-retail" / "hardened"), load(EXAMPLES / "acme-retail" / "hardened"), load_rules())
    assert not report.changed and not report.new_findings and not report.has_security_drift


def test_cli_paths_and_drift_exit_codes(capsys):
    assert main(["paths", str(EXAMPLES / "capital-one-replay")]) == 1
    assert main(["paths", str(EXAMPLES / "acme-retail" / "hardened")]) == 0
    hardened, drifted = str(EXAMPLES / "acme-retail" / "hardened"), str(EXAMPLES / "acme-retail" / "drifted")
    assert main(["drift", hardened, drifted]) == 0
    assert main(["drift", hardened, drifted, "--fail-on-drift"]) == 1
    assert "caused by change to" in capsys.readouterr().out
