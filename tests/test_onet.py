from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from mijobs.sources.base import FetchedArtifact, SourceFetchError
from mijobs.sources.onet import ONetConnector


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _rows() -> list[dict]:
    return [
        {
            "onetsoc_code": "49-9041.00",
            "title": "Industrial Machinery Mechanics",
            "element_id": "2.A.1.a",
            "element_name": "Reading Comprehension",
            "scale_id": "IM",
            "scale_name": "Importance",
            "data_value": 3.5,
            "n": 25,
            "standard_error": 0.12,
            "lower_ci_bound": 3.2,
            "upper_ci_bound": 3.8,
            "recommend_suppress": "N",
            "not_relevant": "N",
            "date_updated": "2026-08-01",
            "domain_source": "Analyst",
        }
    ]


def test_onet_fetch_and_normalize_ratings() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "db_31_0_json/essential_skills.json" in str(request.url)
        return httpx.Response(200, json=_rows(), request=request)

    connector = ONetConnector(_client(handler))
    artifact = connector.fetch_rating_dataset("essential_skills", release="31.0")
    observations = connector.normalize_ratings(artifact)
    assert artifact.dataset_version == "31.0"
    assert observations[0].taxonomy_system == "O*NET-SOC"
    assert observations[0].taxonomy_version == "2019"
    assert observations[0].metadata["database_release"] == "31.0"
    assert observations[0].taxonomy_code == "49-9041.00"
    assert observations[0].metadata["element_name"] == "Reading Comprehension"
    assert observations[0].uncertainty["standard_error"] == 0.12


def test_onet_suppression_and_validation() -> None:
    rows = _rows()
    rows[0]["recommend_suppress"] = "Y"
    artifact = FetchedArtifact(
        source_id="us_onet",
        locator="x",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content=json.dumps(rows).encode(),
        media_type="application/json",
        dataset_version="31.0",
        metadata={"dataset": "essential_skills"},
    )
    assert ONetConnector().normalize_ratings(artifact)[0].release_status == "suppression_recommended"
    with pytest.raises(ValueError):
        ONetConnector().fetch_rating_dataset("not-a-dataset")

    missing_release = FetchedArtifact(
        source_id="us_onet",
        locator="x",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content=b"[]",
        media_type="application/json",
        metadata={"dataset": "essential_skills"},
    )
    with pytest.raises(SourceFetchError):
        ONetConnector().normalize_ratings(missing_release)


def test_onet_healthcheck_and_fetch_failure_paths() -> None:
    assert ONetConnector(_client(lambda req: httpx.Response(200, request=req))).healthcheck() is True

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    assert ONetConnector(_client(broken)).healthcheck() is False
    failed = ONetConnector(_client(lambda req: httpx.Response(404, request=req)))
    with pytest.raises(SourceFetchError):
        failed.fetch_rating_dataset("essential_skills")
    malformed = ONetConnector(_client(lambda req: httpx.Response(200, content=b"{}", request=req)))
    with pytest.raises(SourceFetchError):
        malformed.fetch_rating_dataset("essential_skills")

def test_onet_software_skills_are_categorical_not_fake_ratings() -> None:
    rows = [
        {
            "onetsoc_code": "49-9041.00",
            "title": "Industrial Machinery Mechanics",
            "workplace_example": "Rockwell Automation RSLogix",
            "element_id": "2.B.3",
            "element_name": "Technology Design",
            "hot_technology": "Y",
            "in_demand": "Y",
        }
    ]
    artifact = FetchedArtifact(
        source_id="us_onet",
        locator="x",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content=json.dumps(rows).encode(),
        media_type="application/json",
        dataset_version="31.0",
        metadata={
            "dataset": "software_skills",
            "taxonomy_version": "2019",
            "soc_alignment": "2018",
        },
    )
    item = ONetConnector().normalize_software_skills(artifact)[0]
    assert item.numeric_value is None
    assert item.value_text == "Rockwell Automation RSLogix"
    assert item.taxonomy_version == "2019"
    assert item.metadata["in_demand"] == "Y"


def test_onet_fetch_software_skills_preserves_taxonomy_metadata() -> None:
    payload = [
        {
            "onetsoc_code": "15-1252.00",
            "title": "Software Developers",
            "workplace_example": "Git",
            "element_id": "2.B.3",
            "element_name": "Technology Design",
            "hot_technology": "N",
            "in_demand": "Y",
        }
    ]
    connector = ONetConnector(_client(lambda req: httpx.Response(200, json=payload, request=req)))
    artifact = connector.fetch_rating_dataset("software_skills", release="31.0")
    assert artifact.metadata["taxonomy_version"] == "2019"
    assert artifact.metadata["database_release"] == "31.0"

