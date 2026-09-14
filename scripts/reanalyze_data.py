"""Read every evidence family, verify hashes, and export only public aggregate report context."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from mijobs.artifact_store import ArtifactStore
from mijobs.config import Settings
from mijobs.db import make_engine, session_factory
from mijobs.ledger import audit_evidence_coverage, verify_ledger
from mijobs.models import Base, Observation, SourceArtifact
from mijobs.outlook import monthly_outlook
from mijobs.university_reports import university_report

REPORT = Path("reports/2026-09-13-job-continuity")


def main() -> None:
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    with session_factory(engine)() as session:
        if engine.dialect.name == "sqlite":
            session.connection().exec_driver_sql("PRAGMA query_only=ON")
        chain = verify_ledger(session)
        coverage = audit_evidence_coverage(session)
        if not chain.valid or not coverage.valid:
            raise RuntimeError("Evidence audit failed")
        artifacts = list(session.scalars(select(SourceArtifact)))
        store = ArtifactStore(settings.artifact_root)
        if any(not store.verify(a.content_sha256) for a in artifacts):
            raise RuntimeError("Raw artifact missing or hash mismatch")
        latest = {}
        all_obs = list(session.scalars(select(Observation).order_by(Observation.version)))
        for o in all_obs:
            latest[o.observation_key] = o
        groups = defaultdict(list)
        for o in latest.values():
            groups[(o.metric, o.geography_code, o.unit, o.adjustment)].append(o)
        families = []
        for (metric, geo, unit, adjustment), observations in sorted(
            groups.items(), key=lambda x: str(x[0])
        ):
            dated = sorted(
                (o for o in observations if o.period_start), key=lambda o: o.period_start
            )
            families.append(
                {
                    "metric": metric,
                    "geography_code": geo,
                    "unit": unit,
                    "adjustment": adjustment,
                    "latest_revision_rows": len(observations),
                    "null_numeric_rows": sum(o.numeric_value is None for o in observations),
                    "period_start": str(dated[0].period_start) if dated else None,
                    "period_end": str(max(o.period_end or o.period_start for o in dated))
                    if dated
                    else None,
                }
            )
        manifest = json.loads(Path("config/indicators.json").read_text())
        series = []
        for d in manifest["bls_series"]:
            points = sorted(
                (
                    o
                    for o in latest.values()
                    if o.metric == "bls." + d["series_id"]
                    and o.geography_code == d["geography_code"]
                    and o.period_basis == "monthly"
                ),
                key=lambda o: o.period_start,
            )
            series.append(
                {
                    **d,
                    "status": "available" if points else "missing",
                    "points": [
                        {
                            "date": str(o.period_start),
                            "value": o.numeric_value,
                            "observation_id": o.id,
                            "artifact_id": o.source_artifact_id,
                        }
                        for o in points
                    ],
                }
            )
        for item in series:
            item["outlook"] = monthly_outlook(item["points"], unit=item["unit"])
        universities = university_report(session, year=2024)
        # Do not export raw locators, arbitrary metadata or the database itself.
        university_summary = [
            {
                "unitid": u["unitid"],
                "name": u["name"],
                "awards": u.get("total_first_major_awards"),
                "outcomes": u.get("outcomes", []),
                "michigan_retention_status": u["michigan_retention_status"],
            }
            for u in universities["institutions"]
        ]
        snapshot = {
            "schema": "public-report-analysis/v1",
            "analyzed_at": datetime.now(UTC).isoformat(),
            "ledger": asdict(chain),
            "coverage": asdict(coverage),
            "table_counts": {
                name: session.scalar(select(func.count()).select_from(table))
                for name, table in Base.metadata.tables.items()
            },
            "raw_hashes_verified": len(artifacts),
            "latest_observations": len(latest),
            "families": families,
            "indicators": series,
            "universities": university_summary,
            "additional_observations": [
                {
                    "metric": o.metric,
                    "geography_code": o.geography_code,
                    "value": o.numeric_value,
                    "unit": o.unit,
                    "reference_year": o.metadata_json.get("year"),
                    "period_start": str(o.period_start) if o.period_start else None,
                    "period_end": str(o.period_end) if o.period_end else None,
                    "observation_id": o.id,
                    "artifact_id": o.source_artifact_id,
                    "margin_of_error": o.metadata_json.get("margin_of_error"),
                }
                for o in latest.values()
                if o.metric.startswith(("bea.", "acs.", "qcew.", "bls.underutilization.", "hud."))
            ],
            "artifacts": [
                {
                    "id": a.id,
                    "source_id": a.source_id,
                    "sha256": a.content_sha256,
                    "retrieved_at": a.retrieved_at.isoformat(),
                }
                for a in artifacts
            ],
            "limitations": [
                "Integrity is not accuracy or freshness.",
                "Catalog sources may have no ingested data.",
                "No individual skills, vacancies, placements or residence inferred.",
            ],
        }
        REPORT.joinpath("analysis-snapshot.json").write_text(
            json.dumps(snapshot, indent=2) + "\n", encoding="utf-8"
        )
        text = [
            "# Scripted full-store reanalysis",
            "",
            f"Analyzed {snapshot['analyzed_at']}. Read-only; no harvest or database initialization in this script.",
            "",
            f"Ledger valid: {chain.valid}; events: {chain.event_count}; raw artifact hashes verified: {len(artifacts)}.",
            "",
            f"Ledger head: `{chain.head_hash}`",
            "",
            "| Evidence table | All versions |",
            "|---|---:|",
        ]
        text += [f"| {name} | {count} |" for name, count in snapshot["table_counts"].items()]
        text += [
            "",
            "Latest versions are selected by observation key, not by month. The structured snapshot preserves every metric/geography/unit/adjustment coverage group and the configured trend series with observation/artifact IDs.",
            "",
            "All educational institutions are candidates only; data coverage does not indicate representation or participation.",
            "| Candidate institution | First-major awards | Michigan retention |",
            "|---|---:|---|",
        ]
        text += [
            f"| {u['name']} | {u['awards']} | {u['michigan_retention_status']} |"
            for u in university_summary
        ]
        text += [
            "",
            "Awards are credentials, not available workers. Scorecard outcomes retain separate cohort definitions. Historical QWI is not current demand. Public research outside the ledger remains separately cited. See [snapshot](analysis-snapshot.json) and [evidence definitions](evidence.md).",
        ]
        REPORT.joinpath("data-reanalysis.md").write_text("\n".join(text) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "ledger_events": chain.event_count,
                    "raw_hashes_verified": len(artifacts),
                    "observations": len(all_obs),
                    "available_indicator_series": sum(bool(s["points"]) for s in series),
                }
            )
        )


if __name__ == "__main__":
    main()
