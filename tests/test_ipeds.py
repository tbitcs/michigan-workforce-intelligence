from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime

import httpx
import pytest

from mijobs.sources.base import FetchedArtifact, SourceFetchError
from mijobs.sources.ipeds import IPEDSConnector


def _zip_csv(name: str, body: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, body)
    return buffer.getvalue()


def _artifact(body: str, *, filename: str = "C2024_A.zip", status: str = "final") -> FetchedArtifact:
    return FetchedArtifact(
        source_id="us_nces_ipeds",
        locator=f"https://nces.ed.gov/ipeds/datacenter/data/{filename}",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content=_zip_csv(filename.replace(".zip", ".csv"), body),
        media_type="application/zip",
        dataset_version="2024",
        metadata={"filename": filename, "release_status": status, "collection_year": 2024},
    )


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_ipeds_completions_preserve_cip_award_level_and_release() -> None:
    artifact = _artifact(
        "UNITID,CIPCODE,AWLEVEL,CTOTALT\n171100,15.0404,5,42\n171100,11.0101,7,9\n"
    )
    observations = IPEDSConnector().normalize_completions(
        artifact,
        collection_year=2024,
        cip_version="2020",
        allowed_award_levels={"5"},
    )
    assert len(observations) == 1
    item = observations[0]
    assert item.observation_key == "ipeds:2024:completions:171100:15.0404:5"
    assert item.numeric_value == 42
    assert item.unit == "awards"
    assert item.taxonomy_system == "CIP"
    assert item.taxonomy_version == "2020"
    assert item.taxonomy_code == "15.0404"
    assert item.period_start.isoformat() == "2023-07-01"
    assert item.period_end.isoformat() == "2024-06-30"
    assert item.release_status == "final"


def test_ipeds_12_month_and_fall_enrollment_are_semantically_distinct() -> None:
    e12 = _artifact(
        "UNITID,EFFYLEV,EFYTOTLT\n171100,1,22000\n171100,2,15000\n",
        filename="EFFY2024.zip",
        status="provisional",
    )
    connector = IPEDSConnector()
    annual = connector.normalize_12month_enrollment(
        e12, collection_year=2024, allowed_level_codes={"1"}
    )[0]
    assert annual.metric == "ipeds.enrollment.12_month_unduplicated"
    assert annual.period_basis == "12_month"
    assert annual.metadata["unduplicated_headcount"] is True

    fall = _artifact(
        "UNITID,EFALEVEL,EFTOTLT\n171100,1,18500\n",
        filename="EF2024A.zip",
        status="final",
    )
    snapshot = connector.normalize_fall_enrollment(fall, collection_year=2024)[0]
    assert snapshot.metric == "ipeds.enrollment.fall"
    assert snapshot.period_basis == "fall_2024"
    assert snapshot.period_start is None
    assert snapshot.numeric_value == 18500


def test_ipeds_directory_can_limit_to_michigan() -> None:
    artifact = _artifact(
        "UNITID,INSTNM,STABBR,CITY,COUNTYCD,COUNTYNM,CONTROL\n"
        "171100,Example Michigan University,MI,Detroit,26163,Wayne County,1\n"
        "999999,Example Ohio University,OH,Toledo,39095,Lucas County,1\n",
        filename="HD2024.zip",
    )
    items = IPEDSConnector().normalize_institutions(
        artifact, collection_year=2024, state_filter="MI"
    )
    assert len(items) == 1
    assert items[0].geography_name == "Example Michigan University"
    assert items[0].geography_code == "171100"
    assert items[0].metadata["countycd"] == "26163"


def test_ipeds_fetch_validates_zip_release_and_filename() -> None:
    payload = _zip_csv("c2024_a.csv", "UNITID,CIPCODE,AWLEVEL,CTOTALT\n1,11.0101,5,2\n")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    connector = IPEDSConnector(_client(handler))
    artifact = connector.fetch_data_file(
        "C2024_A.zip", collection_year=2024, release_status="final"
    )
    assert artifact.metadata["release_status"] == "final"
    assert artifact.media_type == "application/zip"
    with pytest.raises(ValueError):
        connector.fetch_data_file("../bad.zip", collection_year=2024, release_status="final")
    with pytest.raises(ValueError):
        connector.fetch_data_file("C2024_A.zip", collection_year=2024, release_status="draft")


def test_ipeds_failure_paths_are_explicit() -> None:
    connector = IPEDSConnector(_client(lambda req: httpx.Response(200, content=b"not zip", request=req)))
    with pytest.raises(SourceFetchError):
        connector.fetch_data_file("C2024_A.zip", collection_year=2024, release_status="final")

    bad_release = _artifact("UNITID,CIPCODE,AWLEVEL,CTOTALT\n1,11.0101,5,2\n", status="unknown")
    with pytest.raises(SourceFetchError):
        IPEDSConnector().normalize_completions(
            bad_release, collection_year=2024, cip_version="2020"
        )

    missing = _artifact("UNITID,CIPCODE\n1,11.0101\n")
    with pytest.raises(SourceFetchError):
        IPEDSConnector().normalize_completions(missing, collection_year=2024, cip_version="2020")


def test_ipeds_healthcheck_handles_network_error() -> None:
    assert IPEDSConnector(_client(lambda req: httpx.Response(200, request=req))).healthcheck() is True

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    assert IPEDSConnector(_client(broken)).healthcheck() is False
