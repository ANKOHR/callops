from __future__ import annotations

from pathlib import Path


def test_html_report_and_readme_carry_simulation_boundary(tmp_path, cli):
    root = Path(__file__).resolve().parents[1]
    assert cli(tmp_path, "call", "--scenario", "discovery").returncode == 0
    result = cli(tmp_path, "report", "discovery-demo", "--format", "html")
    assert result.returncode == 0
    report = (tmp_path / "sessions" / "discovery-demo.report.html").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "SIMULATED CALL" in result.stdout
    assert "SIMULATED CALL" in report
    assert "Demo mode. No real telephony." in report
    assert "Honesty boundary" in readme
    assert "no phone provider integration" in readme
    assert "fictional" in readme


def test_all_cli_subcommands_smoke(tmp_path, cli):
    call = cli(tmp_path, "call", "--scenario", "discovery")
    assert call.returncode == 0
    assert cli(tmp_path, "notes", "discovery-demo").returncode == 0
    assert cli(tmp_path, "actions", "discovery-demo").returncode == 0
    assert cli(tmp_path, "report", "discovery-demo").returncode == 0
    assert cli(tmp_path, "report", "discovery-demo", "--format", "html").returncode == 0
    assert cli(tmp_path, "approve", "act-discovery-demo-01", "--by", "Test Human").returncode == 0
    assert cli(tmp_path, "done", "act-discovery-demo-01", "--by", "Test Human").returncode == 0
