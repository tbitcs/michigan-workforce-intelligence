from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest
from openpyxl import Workbook

from mijobs.sources.base import FetchedArtifact, SourceFetchError
from mijobs.sources.michigan_xlsx import MCDAOEWSParser, MCDAProjectionParser


def _xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _artifact(content: bytes, version: str) -> FetchedArtifact:
    return FetchedArtifact(
        source_id="mi_mcda_projections",
        locator="https://www.michigan.gov/mcda/example.xlsx",
        retrieved_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        dataset_version=version,
    )


def test_projection_parser_detects_headers_and_preserves_horizon() -> None:
    artifact = _artifact(
        _xlsx(
            [
                ["Michigan Long-Term Occupational Projections"],
                ["SOC Code", "Occupation Title", "2024 Employment", "2034 Employment", "Projected Annual Openings", "Projected Growth"],
                ["49-9041", "Industrial Machinery Mechanics", 14000, 15820, 1900, 13.0],
            ]
        ),
        "2024-2034",
    )
    items = MCDAProjectionParser().normalize(artifact)
    by_metric = {item.metric: item for item in items}
    assert by_metric["mcda.projection.occupation.annual_openings"].numeric_value == 1900
    assert by_metric["mcda.projection.occupation.annual_openings"].unit == "jobs_per_year"
    assert by_metric["mcda.projection.occupation.projected_employment"].period_basis == "projected_year_2034"
    assert by_metric["mcda.projection.occupation.percent_change"].numeric_value == 13
    assert all(item.taxonomy_version == "2018" for item in items)


def test_projection_parser_fails_closed_when_schema_is_not_recognized() -> None:
    artifact = _artifact(_xlsx([["Thing", "Value"], ["x", 1]]), "2024-2034")
    with pytest.raises(SourceFetchError):
        MCDAProjectionParser().normalize(artifact)


def test_oews_parser_keeps_snapshot_caveat_and_suppressed_values() -> None:
    artifact = _artifact(
        _xlsx(
            [
                ["2025 Michigan OEWS"],
                ["OCC_CODE", "OCC_TITLE", "TOT_EMP", "EMP_PRSE", "H_MEAN", "H_MEDIAN", "A_MEAN", "A_MEDIAN"],
                ["17-2112", "Industrial Engineers", "31,120", 2.4, 50.25, 48.40, 104520, 100670],
                ["00-0000", "All Occupations", "**", None, None, 23.69, None, 49270],
            ]
        ),
        "2025",
    )
    items = MCDAOEWSParser().normalize(artifact)
    industrial = [item for item in items if item.taxonomy_code == "17-2112"]
    assert len(industrial) == 6
    employment = next(item for item in industrial if item.metric == "mcda.oews.employment")
    assert employment.numeric_value == 31120
    assert "snapshot estimate" in employment.metadata["methodology_caveat"]
    all_jobs = next(
        item
        for item in items
        if item.taxonomy_code == "00-0000" and item.metric == "mcda.oews.employment"
    )
    assert all_jobs.value_text == "**"
    assert all_jobs.numeric_value is None


def test_invalid_xlsx_is_rejected() -> None:
    with pytest.raises(SourceFetchError):
        MCDAOEWSParser().normalize(_artifact(b"not-xlsx", "2025"))
