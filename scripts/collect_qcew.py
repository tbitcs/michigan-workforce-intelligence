"""Collect official quarterly payroll employment/wages and net year-over-year change."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, date, datetime
from decimal import Decimal

from mijobs.artifact_store import ArtifactStore
from mijobs.config import Settings
from mijobs.db import make_engine, session_factory
from mijobs.domain import ObservationInput
from mijobs.ingestion import Ingestor
from mijobs.sources.base import FetchedArtifact
from mijobs.sources.http_policy import governed_client
from mijobs.university_reports import require_audit


def main() -> None:
    settings = Settings.from_env()
    with (
        governed_client(timeout=120) as client,
        session_factory(make_engine(settings.database_url))() as session,
    ):
        require_audit(session)
        ingestor = Ingestor(session, ArtifactStore(settings.artifact_root), actor="qcew-report")
        for geo in ["26099", "26125", "26163", "26000"]:
            url = f"https://data.bls.gov/cew/data/api/2026/1/area/{geo}.csv"
            response = client.get(url)
            response.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(response.text)))
            total = [r for r in rows if r["own_code"] == "0" and r["industry_code"] == "10"]
            if len(total) != 1:
                raise ValueError(f"Expected one total QCEW row for {geo}")
            row = total[0]
            observations = []
            for field, unit in [
                ("month3_emplvl", "jobs"),
                ("avg_wkly_wage", "USD_per_week"),
                ("oty_month3_emplvl_chg", "jobs"),
                ("oty_month3_emplvl_pct_chg", "percent"),
            ]:
                value = row[field]
                observations.append(
                    ObservationInput(
                        observation_key=f"qcew:2026Q1:{geo}:{field}",
                        metric="qcew." + field,
                        value_text=value,
                        numeric_value=Decimal(value),
                        unit=unit,
                        geography_type="state" if geo == "26000" else "county",
                        geography_code="26" if geo == "26000" else geo,
                        period_start=date(2026, 1, 1),
                        period_end=date(2026, 3, 31),
                        period_basis="quarterly",
                        adjustment="not_seasonally_adjusted",
                        metadata={
                            "employment_reference": "March 2026",
                            "wages_reference": "Q1 2026",
                            "ownership": "all",
                            "source_url": url,
                            "change_definition": "year-over-year net payroll employment change, not gross job losses",
                        },
                    )
                )
            ingestor.ingest(
                FetchedArtifact(
                    source_id="us_bls_qcew",
                    locator=url,
                    retrieved_at=datetime.now(UTC),
                    content=response.content,
                    media_type="text/csv",
                    parser_version="qcew-area/1",
                ),
                normalizer=lambda _, items=observations: items,
            )
        session.commit()
        require_audit(session)
        print(
            json.dumps(
                {"geographies": 4, "observations": 16, "period": "2026Q1", "status": "audited"}
            )
        )


if __name__ == "__main__":
    main()
