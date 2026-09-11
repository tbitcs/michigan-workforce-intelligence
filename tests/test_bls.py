from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from mijobs.sources.base import FetchedArtifact, SourceFetchError
from mijobs.sources.bls import BLSConnector


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _sample_payload() -> dict:
    return {
        "status": "REQUEST_SUCCEEDED",
        "Results": {
            "series": [
                {
                    "seriesID": "LASST260000000000003",
                    "catalog": {"series_title": "Michigan unemployment rate"},
                    "data": [
                        {
                            "year": "2026",
                            "period": "M02",
                            "periodName": "February",
                            "value": "5.1",
                            "footnotes": [{}],
                        },
                        {
                            "year": "2025",
                            "period": "M13",
                            "periodName": "Annual",
                            "value": "4.8",
                            "footnotes": [{"code": "P", "text": "Preliminary"}],
                        },
                    ],
                }
            ]
        },
    }


def test_bls_fetch_redacts_api_key_and_records_request() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json=_sample_payload(), request=request)

    connector = BLSConnector(api_key="secret", client=_client(handler))
    artifact = connector.fetch_series(
        ["LASST260000000000003"], start_year=2025, end_year=2026
    )
    assert captured["registrationkey"] == "secret"
    assert "registrationkey" not in artifact.metadata["request"]
    assert artifact.source_id == "us_bls_api"
    assert artifact.media_type == "application/json"


def test_bls_normalizes_month_end_and_annual_average() -> None:
    artifact = FetchedArtifact(
        source_id="us_bls_api",
        locator="https://api.bls.gov/example",
        retrieved_at=__import__("datetime").datetime(2026, 9, 11),
        content=json.dumps(_sample_payload()).encode(),
        media_type="application/json",
    )
    observations = BLSConnector().normalize(
        artifact,
        geography_type="state",
        geography_code="26",
        geography_name="Michigan",
        metric_prefix="laus",
        unit="percent",
    )
    monthly, annual = observations
    assert monthly.period_start == date(2026, 2, 1)
    assert monthly.period_end == date(2026, 2, 28)
    assert monthly.period_basis == "monthly"
    assert monthly.geography_code == "26"
    assert monthly.metric == "laus.LASST260000000000003"
    assert annual.period_start == date(2025, 1, 1)
    assert annual.period_end == date(2025, 12, 31)
    assert annual.period_basis == "annual_average"
    assert annual.release_status == "preliminary"


def test_bls_validates_request_shape() -> None:
    connector = BLSConnector(client=_client(lambda req: httpx.Response(500, request=req)))
    with pytest.raises(ValueError):
        connector.fetch_series([], start_year=2020, end_year=2021)
    with pytest.raises(ValueError):
        connector.fetch_series(["x"], start_year=2027, end_year=2026)
    with pytest.raises(ValueError):
        connector.fetch_series(["x"], start_year=2000, end_year=2026)


def test_bls_rejects_failed_api_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "REQUEST_FAILED", "message": ["bad series"]},
            request=request,
        )

    with pytest.raises(SourceFetchError):
        BLSConnector(client=_client(handler)).fetch_series(["bad"], start_year=2026, end_year=2026)


def test_bls_healthcheck_and_bad_json_paths() -> None:
    ok = BLSConnector(client=_client(lambda req: httpx.Response(200, request=req)))
    assert ok.healthcheck() is True

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    assert BLSConnector(client=_client(broken)).healthcheck() is False

    invalid = BLSConnector(client=_client(lambda req: httpx.Response(200, content=b"nope", request=req)))
    with pytest.raises(SourceFetchError):
        invalid.fetch_series(["x"], start_year=2026, end_year=2026)


def test_bls_normalize_invalid_payload_and_non_numeric_value() -> None:
    bad = FetchedArtifact(
        source_id="us_bls_api",
        locator="x",
        retrieved_at=__import__("datetime").datetime(2026, 9, 11),
        content=b"{}",
        media_type="application/json",
    )
    with pytest.raises(SourceFetchError):
        BLSConnector().normalize(bad)

    body = _sample_payload()
    body["Results"]["series"][0]["data"] = [
        {"year": "2026", "period": "Q01", "value": "not-numeric", "footnotes": []}
    ]
    artifact = FetchedArtifact(
        source_id="us_bls_api",
        locator="x",
        retrieved_at=__import__("datetime").datetime(2026, 9, 11),
        content=json.dumps(body).encode(),
        media_type="application/json",
    )
    obs = BLSConnector().normalize(artifact)[0]
    assert obs.numeric_value is None
    assert obs.period_basis == "Q01"
