"""Collect public BLS underutilization and the official HUD homelessness publication."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from mijobs.artifact_store import ArtifactStore
from mijobs.config import Settings
from mijobs.db import make_engine, session_factory
from mijobs.domain import ObservationInput
from mijobs.ingestion import Ingestor
from mijobs.sources.base import FetchedArtifact
from mijobs.sources.http_policy import governed_client
from mijobs.university_reports import require_audit


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in {"td", "th"}:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row:
            self.rows.append(self.row)


def main():
    settings = Settings.from_env()
    names = {
        "Total, all states": "US",
        "Michigan": "26",
        "Ohio": "39",
        "California": "06",
        "Texas": "48",
        "Florida": "12",
        "Indiana": "18",
        "Illinois": "17",
        "Wisconsin": "55",
        "North Carolina": "37",
    }
    url = "https://www.bls.gov/lau/stalt26q2.htm"
    with governed_client(timeout=120, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        parser = TableRows()
        parser.feed(response.text)
        selected = [row for row in parser.rows if row[0] in names and len(row) == 7]
        if len(selected) != len(names):
            raise ValueError("Review underutilization table schema")
        now = datetime.now(UTC)
        observations = []
        for row in selected:
            for index, value in enumerate(row[1:], 1):
                observations.append(
                    ObservationInput(
                        observation_key=f"bls:underutilization:2026q2:{names[row[0]]}:u{index}",
                        metric=f"bls.underutilization.u{index}",
                        numeric_value=Decimal(value),
                        value_text=value,
                        unit="percent",
                        geography_type="national" if names[row[0]] == "US" else "state",
                        geography_code=names[row[0]],
                        period_start=date(2025, 7, 1),
                        period_end=date(2026, 6, 30),
                        period_basis="11_month_average_excluding_2025_10",
                        adjustment="not_seasonally_adjusted",
                        metadata={
                            "missing_month": "2025-10",
                            "source_url": url,
                            "definition": "BLS U-1 through U-6; overlapping measures, not additive",
                        },
                    )
                )
        with session_factory(make_engine(settings.database_url))() as session:
            require_audit(session)
            ingestor = Ingestor(
                session, ArtifactStore(settings.artifact_root), actor="broader-hardship"
            )
            artifact, _ = ingestor.ingest(
                FetchedArtifact(
                    source_id="us_bls_api",
                    locator=url,
                    retrieved_at=now,
                    content=response.content,
                    media_type="text/html",
                    parser_version="bls-state-underutilization/1",
                ),
                normalizer=lambda _: observations,
            )
            session.commit()
            require_audit(session)
        out = Path("reports/2026-09-13-job-continuity")
        out.joinpath("underutilization.json").write_text(
            json.dumps(
                {
                    "source_url": url,
                    "artifact_id": artifact.id,
                    "retrieved_at": now.isoformat(),
                    "period": "July 2025-June 2026; 11 months, October 2025 missing",
                    "rows": [
                        {
                            "name": r[0],
                            "geography_code": names[r[0]],
                            **{f"u{i}": float(v) for i, v in enumerate(r[1:], 1)},
                        }
                        for r in selected
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        hud_url = "https://www.huduser.gov/portal/sites/default/files/pdf/2025-AHAR-Part-1.pdf"
        hud = client.get(hud_url)
        hud.raise_for_status()
        cache = Path(".cache/hud")
        cache.mkdir(parents=True, exist_ok=True)
        if not hud.content.startswith(b"%PDF"):
            print("HUD PDF unavailable: no valid PDF returned; not ingested")
        else:
            cache.joinpath("2025-AHAR-Part-1.pdf").write_bytes(hud.content)
        print(
            json.dumps(
                {
                    "underutilization_rows": len(selected),
                    "observations": len(observations),
                    "hud_bytes": len(hud.content),
                }
            )
        )


if __name__ == "__main__":
    main()
