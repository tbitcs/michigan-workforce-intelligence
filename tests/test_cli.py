from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mijobs.cli import app

runner = CliRunner()


def test_cli_sources_returns_catalog() -> None:
    result = runner.invoke(app, ["sources"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert any(source["id"] == "mi_mcda_laus" for source in payload["sources"])


def test_cli_init_and_verify_ledger(tmp_path: Path, monkeypatch) -> None:
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    monkeypatch.setenv("MIJOBS_DATABASE_URL", url)
    initialized = runner.invoke(app, ["init-db"])
    assert initialized.exit_code == 0
    assert "database initialized" in initialized.stdout
    assert url not in initialized.stdout
    verified = runner.invoke(app, ["verify-ledger"])
    assert verified.exit_code == 0
    payload = json.loads(verified.stdout)
    assert payload["valid"] is True
    assert payload["event_count"] == 0

    audited = runner.invoke(app, ["audit-ledger"])
    assert audited.exit_code == 0
    audit_payload = json.loads(audited.stdout)
    assert audit_payload["valid"] is True
    assert audit_payload["chain"]["valid"] is True
    assert audit_payload["coverage"]["valid"] is True


def test_cli_harvest_dry_run() -> None:
    result = runner.invoke(app, ["harvest", "--dry-run"])
    assert result.exit_code == 0
    plan = json.loads(result.stdout)
    assert len(plan) == 2
    assert plan[0]["kind"] == "bls"
    assert plan[1]["kind"] == "qwi"


def test_cli_harvest_dry_run_no_qwi() -> None:
    result = runner.invoke(app, ["harvest", "--dry-run", "--no-include-qwi"])
    assert result.exit_code == 0
    plan = json.loads(result.stdout)
    assert len(plan) == 1
    assert plan[0]["kind"] == "bls"


def test_cli_report_empty_db(tmp_path: Path, monkeypatch) -> None:
    url = f"sqlite:///{tmp_path / 'report.db'}"
    monkeypatch.setenv("MIJOBS_DATABASE_URL", url)
    monkeypatch.setenv("MIJOBS_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    runner.invoke(app, ["init-db"])
    result = runner.invoke(app, ["report", "--as-of", "2026-08-15"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema"] == "mijobs-insights-report/v1"
    assert payload["reporting_period"] == "2026-08"
    # All sections should be insufficient with no data
    for section in payload["sections"]:
        assert section["status"] == "insufficient_data"
