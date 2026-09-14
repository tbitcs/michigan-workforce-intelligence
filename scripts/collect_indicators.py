"""Explicit, governed BLS collection; every series keeps its own geography and units."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from sqlalchemy import select

from mijobs.artifact_store import ArtifactStore
from mijobs.config import Settings
from mijobs.db import make_engine, session_factory
from mijobs.ingestion import Ingestor
from mijobs.models import Observation
from mijobs.sources.base import SourceFetchError
from mijobs.sources.bls import BLSConnector
from mijobs.university_reports import require_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-new", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    rows = json.loads(Path("config/indicators.json").read_text())["bls_series"]
    if args.only_new:
        with session_factory(make_engine(settings.database_url))() as session:
            existing = set(session.scalars(select(Observation.metric).distinct()))
        rows = [r for r in rows if "bls." + r["series_id"] not in existing]
    if not rows:
        print("No new indicator series")
        return
    connector = BLSConnector(settings.bls_api_key)
    artifact = connector.fetch_series(
        [r["series_id"] for r in rows], start_year=2020, end_year=2026
    )
    body = json.loads(artifact.content)
    returned = {s["seriesID"]: s for s in body["Results"]["series"]}
    print(json.dumps({key: value.get("catalog", {}) for key, value in returned.items()}))
    with session_factory(make_engine(settings.database_url))() as session:
        require_audit(session)
        ingestor = Ingestor(
            session, ArtifactStore(settings.artifact_root), actor="indicator-harvest"
        )
        total = 0
        for definition in rows:
            series = returned.get(definition["series_id"])
            if not series or not series.get("data"):
                raise SourceFetchError(f"Missing requested series: {definition['series_id']}")
            # Normalize only this series; retain the unmodified full response as its source.
            one = replace(artifact, content=json.dumps({"Results": {"series": [series]}}).encode())
            observations = connector.normalize(
                one,
                geography_type=definition["geography_type"],
                geography_code=definition["geography_code"],
                geography_name=definition["geography_name"],
                metric_prefix="bls",
                unit=definition["unit"],
            )
            observations = [
                replace(
                    o,
                    adjustment=definition["adjustment"],
                    metadata={
                        **o.metadata,
                        "indicator": definition["metric"],
                        "source_url": definition["source_url"],
                    },
                )
                for o in observations
            ]
            _, stored = ingestor.ingest(artifact, normalizer=lambda _a, items=observations: items)
            total += len(stored)
        session.commit()
        require_audit(session)
    print(json.dumps({"series": len(rows), "observations_processed": total, "status": "audited"}))


if __name__ == "__main__":
    main()
