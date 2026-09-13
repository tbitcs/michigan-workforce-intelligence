"""Fetch reviewed BEA bulk data and authorized O*NET credit graphic, preserving provenance."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from mijobs.sources.http_policy import governed_client


def main() -> None:
    out = Path("reports/2026-09-13-job-continuity")
    with governed_client(timeout=120, follow_redirects=True) as client:
        url = "https://apps.bea.gov/regional/zip/SARPP.zip"
        response = client.get(url)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = [
                n for n in archive.namelist() if n.startswith("SARPP_STATE_") and n.endswith(".csv")
            ]
            if len(names) != 1:
                raise ValueError(f"Review BEA files: {archive.namelist()}")
            records = list(csv.DictReader(io.StringIO(archive.read(names[0]).decode("utf-8-sig"))))
        selected = []
        for row in records:
            if (row.get("GeoName") or "").strip() in {
                "Michigan",
                "Ohio",
                "Indiana",
                "Illinois",
                "Wisconsin",
                "California",
                "Texas",
                "North Carolina",
                "United States",
            } and (row.get("LineCode") or "").strip() == "1":
                selected.append(row)
        if not selected:
            raise ValueError(f"Review BEA schema: {records[:1]}")
        snapshot = {
            "source_url": url,
            "publisher": "U.S. Bureau of Economic Analysis",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "sha256": hashlib.sha256(response.content).hexdigest(),
            "definition": "Regional price parity, all items, United States=100; same-vintage historical series",
            "rows": selected,
        }
        out.joinpath("interstate-prices.json").write_text(json.dumps(snapshot, indent=2) + "\n")
        cache = Path(".cache/reference")
        cache.mkdir(parents=True, exist_ok=True)
        cache.joinpath(snapshot["sha256"]).write_bytes(response.content)
        page = client.get("https://www.onetcenter.org/graphics.html")
        page.raise_for_status()
        links = re.findall(r'href="([^"]+\.zip)"', page.text)
        print(
            json.dumps(
                {
                    "bea_states": len(selected),
                    "bea_columns": list(selected[0]),
                    "onet_graphics": links,
                }
            )
        )


if __name__ == "__main__":
    main()
