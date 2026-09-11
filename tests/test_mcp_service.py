from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from mijobs.config import load_source_catalog
from mijobs.domain import ClaimKind, ClaimStatus
from mijobs.mcp_service import MCPService
from mijobs.repository import EvidenceRepository


def _metric(value: str) -> dict[str, str]:
    return {
        "value": value,
        "unit": "people_per_year",
        "geography_code": "26",
        "period_basis": "annual",
        "taxonomy_system": "SOC",
        "taxonomy_version": "2024",
        "taxonomy_code": "49-9041",
    }


def test_mcp_write_disabled_by_default(db_session: Session) -> None:
    claim = EvidenceRepository(db_session).add_claim(
        claim_key="test",
        text="test",
        kind=ClaimKind.HYPOTHESIS,
        status=ClaimStatus.UNRESOLVED,
    )
    service = MCPService(db_session, load_source_catalog(), write_enabled=False)
    with pytest.raises(PermissionError):
        service.claims_challenge(claim_id=claim.id, rationale="challenge")


def test_mcp_write_can_append_challenge_when_explicitly_enabled(db_session: Session) -> None:
    claim = EvidenceRepository(db_session).add_claim(
        claim_key="test-enabled", text="test", kind=ClaimKind.HYPOTHESIS
    )
    service = MCPService(db_session, load_source_catalog(), write_enabled=True)
    result = service.claims_challenge(claim_id=claim.id, rationale="needs more evidence")
    assert result["status"] == "open"
    assert service.claims_get(claim.id)["effective_status"] == "contested"


def test_mcp_gap_returns_json_safe_decimals(db_session: Session) -> None:
    service = MCPService(db_session, load_source_catalog())
    result = service.gap_training_pipeline(
        {"annual_openings": _metric("100"), "completions": _metric("60")}
    )
    assert result["gap"] == "40"
    assert result["completeness"] == str(Decimal("0.4"))


def test_mcp_policy_scenario_requires_explicit_assumptions_and_returns_json_safe_values(
    db_session: Session,
) -> None:
    service = MCPService(db_session, load_source_catalog())
    assumptions = {
        "annual_training_seats": "100",
        "cost_per_seat": "5000",
        "completion_rate": "0.8",
        "placement_rate": "0.75",
        "michigan_retention_rate": "0.9",
        "counterfactual_entry_share": "0.25",
    }
    result = service.policy_training_scenario(
        {
            "baseline_gap_workers": "100",
            "low": {**assumptions, "completion_rate": "0.6"},
            "base": assumptions,
            "high": {**assumptions, "completion_rate": "0.9"},
        }
    )
    assert Decimal(result["base"]["net_additional_workers"]) == Decimal("40.5")
    assert result["base"]["annual_program_cost"] == "500000"
    with pytest.raises(ValueError, match="high assumption set"):
        service.policy_training_scenario(
            {"baseline_gap_workers": "100", "low": assumptions, "base": assumptions}
        )


def test_mcp_observation_search_defaults_to_latest_version(db_session: Session) -> None:
    from datetime import datetime, timezone
    from mijobs.domain import ObservationInput

    repo = EvidenceRepository(db_session)
    artifact = repo.add_source_artifact(
        source_id="us_bls_api",
        source_locator="https://api.bls.gov/x",
        retrieved_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        content_sha256="b" * 64,
        media_type="application/json",
        byte_size=1,
        local_path="bb/bb/hash",
    )
    repo.add_observation(
        artifact.id,
        ObservationInput(
            observation_key="mi:u:2026-08", metric="unemployment_rate", value_text="5.2", unit="percent"
        ),
    )
    newest = repo.add_observation(
        artifact.id,
        ObservationInput(
            observation_key="mi:u:2026-08", metric="unemployment_rate", value_text="5.1", unit="percent"
        ),
    )
    service = MCPService(db_session, load_source_catalog())
    result = service.observations_search(metric="unemployment_rate")
    assert result["count"] == 1
    assert result["observations"][0]["id"] == newest.id
    all_versions = service.observations_search(metric="unemployment_rate", latest_only=False)
    assert all_versions["count"] == 2


def test_mcp_claim_search_defaults_to_latest_and_exposes_effective_status(db_session: Session) -> None:
    repo = EvidenceRepository(db_session)
    first = repo.add_claim(claim_key="k", text="v1", kind=ClaimKind.INFERRED)
    newest = repo.add_claim(
        claim_key="k", text="v2", kind=ClaimKind.INFERRED, status=ClaimStatus.SUPPORTED
    )
    repo.add_challenge(claim_id=newest.id, rationale="new evidence")
    service = MCPService(db_session, load_source_catalog())
    result = service.claims_search()
    assert result["count"] == 1
    assert result["claims"][0]["id"] == newest.id
    assert result["claims"][0]["effective_status"] == "contested"
    assert service.claims_search(latest_only=False)["count"] == 2
    assert first.id != newest.id


def test_mcp_query_limit_is_bounded(db_session: Session) -> None:
    service = MCPService(db_session, load_source_catalog())
    with pytest.raises(ValueError):
        service.observations_search(limit=0)
    with pytest.raises(ValueError):
        service.claims_search(limit=501)


def test_mcp_artifact_get_returns_provenance(db_session: Session) -> None:
    from datetime import datetime, timezone

    artifact = EvidenceRepository(db_session).add_source_artifact(
        source_id="mi_mcda_qcew",
        source_locator="https://www.michigan.gov/qcew.xlsx",
        retrieved_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        content_sha256="c" * 64,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        byte_size=123,
        local_path="cc/cc/hash",
        dataset_version="2026-Q1",
        parser_version="qcew/1",
    )
    service = MCPService(db_session, load_source_catalog())
    result = service.artifacts_get(artifact.id)
    assert result["content_sha256"] == "c" * 64
    assert result["dataset_version"] == "2026-Q1"
    with pytest.raises(KeyError):
        service.artifacts_get("missing")
