from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from mijobs.domain import ObservationInput
from mijobs.economic_context import economic_coverage, economic_series
from mijobs.ledger import verify_ledger
from mijobs.repository import EvidenceRepository


def test_latest_exact_geography_and_lineage(db_session):
    repo = EvidenceRepository(db_session)
    artifact = repo.add_source_artifact(
        source_id="us_bls_api",
        source_locator="https://www.bls.gov",
        retrieved_at=datetime.now(UTC),
        content_sha256="a" * 64,
        media_type="application/json",
        byte_size=1,
        local_path="a",
    )

    def add(key, value, geo="26099"):
        return repo.add_observation(
            artifact.id,
            ObservationInput(
                observation_key=key,
                metric="laus.unemployment_rate",
                numeric_value=Decimal(value) if value else None,
                value_text=value or "",
                unit="percent",
                geography_type="county",
                geography_code=geo,
                period_start=date(2026, 1, 1),
                period_basis="monthly",
                adjustment="NSA",
                metadata={"indicator": "friendly_alias"},
            ),
        )

    add("revision", "4")
    latest = add("revision", "5")
    add("different", "7", "26125")
    result = economic_series(db_session, geography_code="26099", metric="laus.unemployment_rate")
    assert (
        economic_series(db_session, geography_code="26099", metric="friendly_alias")["status"]
        == "available"
    )
    assert len(result["points"]) == 1
    assert result["points"][0]["observation_id"] == latest.id
    assert result["points"][0]["artifact_id"] == artifact.id
    assert result["points"][0]["value"] == 5
    assert result["points"][0]["unit"] == "percent"
    assert economic_coverage(db_session, "26125")["available"] == [
        {"metric": "laus.unemployment_rate", "geography_code": "26125"}
    ]
    add("missing", None)
    result = economic_series(
        db_session, geography_code="26099", metric="laus.unemployment_rate", limit=1
    )
    assert result["truncated"]
    assert economic_series(db_session, geography_code="26", metric="missing")["status"] == "missing"
    assert verify_ledger(db_session).valid


@pytest.mark.parametrize(
    "geo,metric,limit", [("", "x", 1), ("26", "", 1), ("26", "x", 0), ("26", "x", 501)]
)
def test_invalid_queries(db_session, geo, metric, limit):
    with pytest.raises(ValueError):
        economic_series(db_session, geography_code=geo, metric=metric, limit=limit)
