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
    assert url in initialized.stdout
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
