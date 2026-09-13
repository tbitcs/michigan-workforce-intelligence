"""Collect matching-year ACS earnings/rents and register BEA/ACS public aggregate evidence."""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from PIL import Image

from mijobs.artifact_store import ArtifactStore
from mijobs.config import Settings
from mijobs.db import make_engine, session_factory
from mijobs.domain import ObservationInput
from mijobs.ingestion import Ingestor
from mijobs.sources.base import FetchedArtifact
from mijobs.sources.http_policy import governed_client
from mijobs.university_reports import require_audit


def main() -> None:
    root = Path("reports/2026-09-13-job-continuity")
    bea = json.loads(root.joinpath("interstate-prices.json").read_text())
    url = "https://api.census.gov/data/2024/acs/acs1"
    fields = ["NAME", "B20002_001E", "B20002_001M", "B25064_001E", "B25064_001M"]
    with governed_client(timeout=120, follow_redirects=True) as client:
        r = client.get(
            url,
            params={"get": ",".join(fields), "for": "state:*", "key": os.environ["CENSUS_API_KEY"]},
        )
        if r.status_code != 200:
            raise RuntimeError(f"ACS HTTP {r.status_code}; no credential-bearing URL emitted")
        data = r.json()
        rows = [dict(zip(data[0], row, strict=True)) for row in data[1:]]
        selected = [row for row in rows if row["NAME"] in {v["GeoName"] for v in bea["rows"]}]
        now = datetime.now(UTC)
        settings = Settings.from_env()
        with session_factory(make_engine(settings.database_url))() as session:
            require_audit(session)
            ingestor = Ingestor(
                session, ArtifactStore(settings.artifact_root), actor="interstate-comparison"
            )
            bea_observations = []
            for row in bea["rows"]:
                geo = row["GeoFIPS"].strip(' "')[:2]
                for year in range(2008, 2025):
                    value = row[str(year)].strip()
                    bea_observations.append(
                        ObservationInput(
                            observation_key=f"bea:SARPP:1:{geo}:{year}",
                            metric="bea.rpp.all_items",
                            value_text=value,
                            numeric_value=Decimal(value),
                            unit="US_price_level_100",
                            geography_type="state" if geo != "00" else "national",
                            geography_code=geo,
                            period_basis="annual",
                            metadata={
                                "year": year,
                                "publisher": "BEA",
                                "table": "SARPP",
                                "line": 1,
                            },
                        )
                    )
            bea_raw = Path(".cache/reference", bea["sha256"]).read_bytes()
            artifact, _ = ingestor.ingest(
                FetchedArtifact(
                    source_id="us_bea_regional",
                    locator=bea["source_url"],
                    retrieved_at=datetime.fromisoformat(bea["retrieved_at"]),
                    content=bea_raw,
                    media_type="application/zip",
                    parser_version="bea-sarpp/1",
                ),
                normalizer=lambda _: bea_observations,
            )
            observations = []
            for row in selected:
                for code, metric, unit in [
                    ("B20002", "acs.median_earnings", "USD_2024_per_year"),
                    ("B25064", "acs.median_gross_rent", "USD_per_month"),
                ]:
                    value = Decimal(row[code + "_001E"])
                    moe = Decimal(row[code + "_001M"])
                    observations.append(
                        ObservationInput(
                            observation_key=f"acs:2024:acs1:{code}:{row['state']}",
                            metric=metric,
                            value_text=str(value),
                            numeric_value=value if value >= 0 else None,
                            unit=unit,
                            geography_type="state",
                            geography_code=row["state"],
                            period_basis="acs_1year",
                            metadata={
                                "year": 2024,
                                "margin_of_error": float(moe) if moe >= 0 else None,
                                "variable": code + "_001E",
                                "source_url": url,
                            },
                        )
                    )
            acs_artifact, _ = ingestor.ingest(
                FetchedArtifact(
                    source_id="us_census_acs",
                    locator=url + "#variables=" + ",".join(fields) + "&for=state:*",
                    retrieved_at=now,
                    content=r.content,
                    media_type="application/json",
                    parser_version="acs-state-comparison/1",
                ),
                normalizer=lambda _: observations,
            )
            session.commit()
            require_audit(session)
        root.joinpath("interstate-earnings.json").write_text(
            json.dumps(
                {
                    "source_url": url,
                    "retrieved_at": now.isoformat(),
                    "artifact_id": acs_artifact.id,
                    "sha256": acs_artifact.content_sha256,
                    "bea_artifact_id": artifact.id,
                    "rows": selected,
                    "definition": "ACS 2024 1-year median earnings among people age 16+ with earnings; not occupation-specific or full-time-only; MOEs retained.",
                },
                indent=2,
            )
            + "\n"
        )
        logo_url = "https://www.onetcenter.org/dl_files/link/online_graphics.zip"
        graphic = client.get(logo_url)
        graphic.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(graphic.content)) as archive:
            candidates = []
            for name in archive.namelist():
                if name.lower().endswith(".png"):
                    content = archive.read(name)
                    size = Image.open(io.BytesIO(content)).size
                    candidates.append((size[0], name, content))
            if not candidates:
                raise ValueError("No PNG graphic in approved O*NET archive")
            _, name, content = max(candidates)
        assets = Path("docs/assets")
        assets.mkdir(exist_ok=True)
        assets.joinpath("onet-online.png").write_bytes(content)
        assets.joinpath("onet-credit.json").write_text(
            json.dumps(
                {
                    "source_url": logo_url,
                    "member": name,
                    "retrieved_at": now.isoformat(),
                    "permission_url": "https://www.onetcenter.org/graphics.html",
                    "changes": "Unmodified PNG; proportionally resized for display only.",
                },
                indent=2,
            )
            + "\n"
        )
        print(
            json.dumps(
                {
                    "acs_states": len(selected),
                    "bea_observations": len(bea_observations),
                    "onet_graphic": name,
                }
            )
        )


if __name__ == "__main__":
    main()
