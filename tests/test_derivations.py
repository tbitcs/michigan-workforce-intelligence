from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from mijobs.domain import ClaimKind, EvidenceRelation, EvidenceType, ObservationInput
from mijobs.epistemics import EpistemicService
from mijobs.ledger import audit_evidence_coverage, verify_ledger
from mijobs.repository import EvidenceRepository


def _observation(repo: EvidenceRepository):
    artifact = repo.add_source_artifact(
        source_id="mi_mcda_projections",
        source_locator="https://www.michigan.gov/projections.xlsx",
        retrieved_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
        content_sha256="e" * 64,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        byte_size=10,
        local_path="ee/ee/hash",
        dataset_version="2024-2034",
    )
    obs = repo.add_observation(
        artifact.id,
        ObservationInput(
            observation_key="mi:openings:49-9041",
            metric="annual_openings",
            value_text="1000",
            numeric_value=Decimal("1000"),
            unit="people_per_year",
            geography_type="state",
            geography_code="26",
            taxonomy_system="SOC",
            taxonomy_version="2024",
            taxonomy_code="49-9041",
        ),
    )
    return artifact, obs


def test_derived_metric_is_versioned_ledgered_and_traceable(db_session: Session) -> None:
    repo = EvidenceRepository(db_session, actor="analytics")
    artifact, obs = _observation(repo)
    first = repo.add_derived_metric(
        derivation_key="gap:49-9041:MI",
        formula_name="training_pipeline_gap",
        formula_version="v1",
        metric="training_pipeline_gap",
        value_text="400",
        numeric_value=400.0,
        unit="people_per_year",
        input_refs=[{"type": "observation", "id": obs.id}],
        scope={"geography_code": "26", "soc": "49-9041"},
        assumptions=["Completion-to-occupation mapping is valid for the selected release."],
        caveats=["Pipeline comparison is not proof of realized shortage."],
    )
    revised = repo.add_derived_metric(
        derivation_key="gap:49-9041:MI",
        formula_name="training_pipeline_gap",
        formula_version="v1",
        metric="training_pipeline_gap",
        value_text="375",
        numeric_value=375.0,
        unit="people_per_year",
        input_refs=[{"type": "observation", "id": obs.id}],
    )
    assert revised.version == 2
    assert revised.supersedes_derived_metric_id == first.id
    assert repo.latest_derived_metric(first.derivation_key).id == revised.id

    claim = repo.add_claim(
        claim_key="gap-claim",
        text="The measured training pipeline is below projected openings under formula v1.",
        kind=ClaimKind.DERIVED,
    )
    repo.add_evidence(
        claim_id=claim.id,
        evidence_type=EvidenceType.DERIVED_METRIC,
        evidence_id=revised.id,
        relation=EvidenceRelation.DERIVES_FROM,
    )
    trace = EpistemicService(db_session).trace_claim(claim.id)
    assert trace["evidence"][0]["derived_metric"]["formula_version"] == "v1"
    assert trace["artifacts"][0]["id"] == artifact.id
    assert verify_ledger(db_session).valid
    assert audit_evidence_coverage(db_session).valid


def test_derived_metric_requires_real_inputs(db_session: Session) -> None:
    repo = EvidenceRepository(db_session)
    with pytest.raises(ValueError):
        repo.add_derived_metric(
            derivation_key="x",
            formula_name="f",
            formula_version="1",
            metric="m",
            value_text="1",
            numeric_value=1,
            unit="people",
            input_refs=[],
        )
    with pytest.raises(KeyError):
        repo.add_derived_metric(
            derivation_key="x",
            formula_name="f",
            formula_version="1",
            metric="m",
            value_text="1",
            numeric_value=1,
            unit="people",
            input_refs=[{"type": "observation", "id": "missing"}],
        )


def test_evidence_edge_rejects_dangling_reference(db_session: Session) -> None:
    repo = EvidenceRepository(db_session)
    claim = repo.add_claim(claim_key="c", text="c", kind=ClaimKind.HYPOTHESIS)
    with pytest.raises(KeyError):
        repo.add_evidence(
            claim_id=claim.id,
            evidence_type=EvidenceType.OBSERVATION,
            evidence_id="missing",
            relation=EvidenceRelation.SUPPORTS,
        )
