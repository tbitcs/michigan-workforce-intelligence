from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from mijobs.domain import (
    ChallengeStatus,
    ClaimKind,
    ClaimStatus,
    EvidenceRelation,
    EvidenceType,
    ObservationInput,
)
from mijobs.epistemics import EpistemicService
from mijobs.ledger import verify_ledger
from mijobs.repository import EvidenceRepository


def _artifact(repo: EvidenceRepository):
    return repo.add_source_artifact(
        source_id="us_bls_api",
        source_locator="https://api.bls.gov/example",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content_sha256="a" * 64,
        media_type="application/json",
        byte_size=12,
        local_path="aa/aa/hash",
    )


def test_revision_preserves_old_observation(db_session: Session) -> None:
    repo = EvidenceRepository(db_session, actor="test")
    artifact = _artifact(repo)
    v1 = repo.add_observation(
        artifact.id,
        ObservationInput(
            observation_key="mi:unemployment:2026-08",
            metric="unemployment_rate",
            value_text="5.0",
            numeric_value=Decimal("5.0"),
            unit="percent",
        ),
    )
    v2 = repo.add_observation(
        artifact.id,
        ObservationInput(
            observation_key="mi:unemployment:2026-08",
            metric="unemployment_rate",
            value_text="4.9",
            numeric_value=Decimal("4.9"),
            unit="percent",
            release_status="revised",
        ),
    )
    assert v1.version == 1
    assert v2.version == 2
    assert v2.supersedes_observation_id == v1.id
    assert repo.latest_observation(v1.observation_key).id == v2.id
    assert verify_ledger(db_session).valid


def test_challenge_changes_effective_status_without_mutating_claim(db_session: Session) -> None:
    repo = EvidenceRepository(db_session, actor="test")
    claim = repo.add_claim(
        claim_key="macomb:maintenance-shortage",
        text="Macomb County has a maintenance technician shortage.",
        kind=ClaimKind.INFERRED,
        status=ClaimStatus.SUPPORTED,
    )
    challenge = repo.add_challenge(claim_id=claim.id, rationale="Supply estimate omits commuters.")
    service = EpistemicService(db_session)
    assert claim.status == ClaimStatus.SUPPORTED.value
    assert service.effective_status(claim) == ClaimStatus.CONTESTED.value
    revised = repo.revise_challenge(
        challenge_key=challenge.challenge_key,
        status=ChallengeStatus.RESOLVED,
        resolution_note="Commuter-flow evidence incorporated in a new claim version.",
    )
    assert revised.supersedes_challenge_id == challenge.id
    assert service.effective_status(claim) == ClaimStatus.SUPPORTED.value


def test_claim_trace_reaches_observation_and_artifact(db_session: Session) -> None:
    repo = EvidenceRepository(db_session, actor="test")
    artifact = _artifact(repo)
    obs = repo.add_observation(
        artifact.id,
        ObservationInput(
            observation_key="x",
            metric="employment",
            value_text="100",
            numeric_value=Decimal("100"),
            unit="people",
        ),
    )
    claim = repo.add_claim(
        claim_key="c",
        text="The reported employment value is 100.",
        kind=ClaimKind.REPORTED,
        status=ClaimStatus.SUPPORTED,
    )
    repo.add_evidence(
        claim_id=claim.id,
        evidence_type=EvidenceType.OBSERVATION,
        evidence_id=obs.id,
        relation=EvidenceRelation.SUPPORTS,
    )
    trace = EpistemicService(db_session).trace_claim(claim.id)
    assert trace["evidence"][0]["observation"]["source_artifact_id"] == artifact.id
    assert trace["artifacts"][0]["content_sha256"] == "a" * 64


def test_core_evidence_table_is_immutable(db_session: Session) -> None:
    repo = EvidenceRepository(db_session)
    claim = repo.add_claim(
        claim_key="immutable",
        text="Original",
        kind=ClaimKind.HYPOTHESIS,
    )
    db_session.commit()
    with pytest.raises(DatabaseError):
        db_session.execute(text("UPDATE claims SET text='changed' WHERE id=:id"), {"id": claim.id})
        db_session.commit()
    db_session.rollback()
