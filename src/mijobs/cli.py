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
    typer.echo("database initialized")


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


@app.command("harvest")
def harvest(
    start_year: int = typer.Option(2020, help="Start year for harvest range"),
    end_year: int = typer.Option(2026, help="End year for harvest range"),
    include_qwi: bool = typer.Option(True, help="Include Census QWI tasks"),
    dry_run: bool = typer.Option(False, help="Show plan without executing"),
) -> None:
    """Harvest official data from BLS and Census QWI into the evidence database."""
    from mijobs.artifact_store import ArtifactStore
    from mijobs.harvest import HarvestRunner, default_plan
    from mijobs.sources.bls import BLSConnector
    from mijobs.sources.census import CensusConnector

    settings = Settings.from_env()

    if dry_run:
        tasks = default_plan(start_year=start_year, end_year=end_year, include_qwi=include_qwi)
        plan = [
            {"kind": kind, "task": type(task).__name__, "label": getattr(task, "label", "")}
            for kind, task in tasks
        ]
        typer.echo(json.dumps(plan, indent=2))
        return

    engine = make_engine(settings.database_url)
    initialize_database(engine)
    factory = session_factory(engine)

    store = ArtifactStore(settings.artifact_root)
    bls = BLSConnector(api_key=settings.bls_api_key) if settings.bls_api_key else None
    census = CensusConnector(settings.census_api_key) if settings.census_api_key else None

    tasks = default_plan(start_year=start_year, end_year=end_year, include_qwi=include_qwi)

    with factory() as session:
        runner = HarvestRunner(session, store, bls=bls, census=census, actor="cli-harvest")
        report = runner.run(tasks)
        session.commit()

    typer.echo(json.dumps(report.to_dict(), indent=2))
    if report.failed > 0:
        raise typer.Exit(1)


@app.command("report")
def report(
    as_of: str = typer.Option(None, help="Reference date YYYY-MM-DD (default: today)"),
) -> None:
    """Generate the structured insights report from harvested data."""
    from datetime import date as _date

    from mijobs.insights_report import InsightsReportGenerator

    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine)
    factory = session_factory(engine)

    ref_date = _date.fromisoformat(as_of) if as_of else None

    with factory() as session:
        generator = InsightsReportGenerator(session, actor="cli-report")
        insights = generator.generate(as_of=ref_date)
        session.commit()

    typer.echo(json.dumps(insights.to_dict(), indent=2))


@app.command("harvest-universities")
def harvest_universities_command(year: int = typer.Option(2024, min=2020, max=2024)) -> None:
    """Load reviewed IPEDS completions, official crosswalk and PSEO coverage."""
    from mijobs.artifact_store import ArtifactStore
    from mijobs.university_reports import harvest_universities

    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine)
    with session_factory(engine)() as session:
        result = harvest_universities(session, ArtifactStore(settings.artifact_root), year=year)
        session.commit()
    typer.echo(json.dumps(result, indent=2))


@app.command("report-universities")
def report_universities_command(year: int = typer.Option(2024, min=2020, max=2024)) -> None:
    """Read-only university report with source-linked program awards and pathways."""
    from mijobs.university_reports import university_report

    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    initialize_database(engine)
    with session_factory(engine)() as session:
        result = university_report(session, year=year)
    typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
