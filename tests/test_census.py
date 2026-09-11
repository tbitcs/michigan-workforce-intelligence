from __future__ import annotations

import json
from datetime import datetime

import httpx
import pytest

from mijobs.sources.base import FetchedArtifact, SourceFetchError
from mijobs.sources.census import CensusConnector


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_qwi_requires_key_and_endpoint_allowlist() -> None:
    connector = CensusConnector(None)
    with pytest.raises(SourceFetchError):
        connector.fetch_qwi(endpoint="sa", indicators=["Emp"], geography="state:26", time="latest")
    with pytest.raises(ValueError):
        CensusConnector("k").fetch_qwi(
            endpoint="not-real", indicators=["Emp"], geography="state:26", time="latest"
        )


def test_qwi_fetch_does_not_persist_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["key"] == "secret"
        return httpx.Response(
            200,
            json=[["Emp", "state"], ["100", "26"]],
            request=request,
        )

    artifact = CensusConnector("secret", _client(handler)).fetch_qwi(
        endpoint="sa", indicators=["Emp"], geography="state:26", time="2026-Q1"
    )
    assert "secret" not in artifact.locator
    assert "key" not in artifact.metadata["request"]
    assert artifact.metadata["endpoint"] == "sa"


def test_census_rows_parses_tabular_json() -> None:
    artifact = FetchedArtifact(
        source_id="us_census_qwi",
        locator="x",
        retrieved_at=datetime(2026, 9, 11),
        content=json.dumps([["Emp", "state"], [100, "26"]]).encode(),
        media_type="application/json",
    )
    assert CensusConnector.rows(artifact) == [{"Emp": "100", "state": "26"}]


def test_census_rows_rejects_malformed_shape() -> None:
    artifact = FetchedArtifact(
        source_id="us_census_qwi",
        locator="x",
        retrieved_at=datetime(2026, 9, 11),
        content=b'{"not": "tabular"}',
        media_type="application/json",
    )
    with pytest.raises(SourceFetchError):
        CensusConnector.rows(artifact)


def test_qwi_healthcheck_success_failure_and_indicator_validation() -> None:
    ok = CensusConnector(
        "k", _client(lambda req: httpx.Response(200, json=[["Emp"], ["1"]], request=req))
    )
    assert ok.healthcheck() is True
    assert CensusConnector(None).healthcheck() is False

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    assert CensusConnector("k", _client(broken)).healthcheck() is False
    with pytest.raises(ValueError):
        ok.fetch_qwi(endpoint="sa", indicators=[], geography="state:26", time="latest")


def test_qwi_rejects_http_and_non_json() -> None:
    http_fail = CensusConnector(
        "k", _client(lambda req: httpx.Response(500, content=b"bad", request=req))
    )
    with pytest.raises(SourceFetchError):
        http_fail.fetch_qwi(endpoint="sa", indicators=["Emp"], geography="state:26", time="latest")
    not_json = CensusConnector(
        "k", _client(lambda req: httpx.Response(200, content=b"bad", request=req))
    )
    with pytest.raises(SourceFetchError):
        not_json.fetch_qwi(endpoint="sa", indicators=["Emp"], geography="state:26", time="latest")


def test_census_rows_rejects_width_mismatch() -> None:
    artifact = FetchedArtifact(
        source_id="us_census_qwi",
        locator="x",
        retrieved_at=datetime(2026, 9, 11),
        content=json.dumps([["Emp", "state"], ["100"]]).encode(),
        media_type="application/json",
    )
    with pytest.raises(SourceFetchError):
        CensusConnector.rows(artifact)


def test_qwi_normalizer_preserves_quarter_geography_taxonomy_and_dimensions() -> None:
    artifact = FetchedArtifact(
        source_id="us_census_qwi",
        locator="x",
        retrieved_at=datetime(2026, 9, 11),
        content=json.dumps(
            [
                ["Emp", "EarnS", "time", "state", "county", "industry", "sex"],
                ["1234", "5678.90", "2026-Q1", "26", "099", "31-33", "0"],
            ]
        ).encode(),
        media_type="application/json",
    )
    observations = CensusConnector("k").normalize_qwi(
        artifact,
        indicator_units={"Emp": "jobs", "EarnS": "dollars"},
        geography_type="county",
        geography_fields=("state", "county"),
        taxonomy_system="NAICS",
        taxonomy_version="2022",
        taxonomy_field="industry",
    )
    emp, earn = observations
    assert emp.geography_code == "26:099"
    assert emp.period_start.isoformat() == "2026-01-01"
    assert emp.period_end.isoformat() == "2026-03-31"
    assert emp.period_basis == "quarterly"
    assert emp.taxonomy_code == "31-33"
    assert emp.metadata["dimensions"]["sex"] == "0"
    assert emp.numeric_value == 1234
    assert earn.unit == "dollars"


def test_qwi_normalizer_refuses_implicit_units_and_missing_geography() -> None:
    artifact = FetchedArtifact(
        source_id="us_census_qwi",
        locator="x",
        retrieved_at=datetime(2026, 9, 11),
        content=json.dumps([["Emp", "time", "state"], ["1", "2026-Q1", "26"]]).encode(),
        media_type="application/json",
    )
    connector = CensusConnector("k")
    with pytest.raises(ValueError):
        connector.normalize_qwi(
            artifact, indicator_units={}, geography_type="state", geography_fields=("state",)
        )
    with pytest.raises(SourceFetchError):
        connector.normalize_qwi(
            artifact,
            indicator_units={"Emp": "jobs"},
            geography_type="county",
            geography_fields=("state", "county"),
        )
