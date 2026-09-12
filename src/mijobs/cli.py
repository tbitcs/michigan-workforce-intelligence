from __future__ import annotations

import json
from dataclasses import asdict

import typer

from mijobs.config import Settings, load_source_catalog
from mijobs.db import initialize_database, make_engine, session_factory
from mijobs.ledger import audit_evidence_coverage, verify_ledger

app = typer.Typer(no_args_is_help=True, help="Michigan Workforce Intelligence administration CLI")


@app.command("init-db")
def init_db() -> None:
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine)
    typer.echo(f"initialized {settings.database_url}")


@app.command("verify-ledger")
def verify_chain() -> None:
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine)
    factory = session_factory(engine)
    with factory() as session:
        result = verify_ledger(session)
    typer.echo(json.dumps(asdict(result), indent=2))
    if not result.valid:
        raise typer.Exit(2)


@app.command("audit-ledger")
def audit_ledger() -> None:
    """Verify hash-chain integrity and that no evidence-bearing row bypassed it."""
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine)
    factory = session_factory(engine)
    with factory() as session:
        chain = verify_ledger(session)
        coverage = audit_evidence_coverage(session)
    result = {
        "valid": chain.valid and coverage.valid,
        "chain": asdict(chain),
        "coverage": asdict(coverage),
    }
    typer.echo(json.dumps(result, indent=2))
    if not result["valid"]:
        raise typer.Exit(2)


@app.command("sources")
def sources() -> None:
    catalog = load_source_catalog()
    typer.echo(json.dumps(catalog.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    app()
