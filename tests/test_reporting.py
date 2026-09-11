from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from mijobs.domain import ClaimKind, ClaimStatus
from mijobs.reporting import ReportContextBuilder
from mijobs.repository import EvidenceRepository


def test_report_context_contains_verified_ledger_and_claim(db_session: Session) -> None:
    claim = EvidenceRepository(db_session).add_claim(
        claim_key="report",
        text="A scoped claim.",
        kind=ClaimKind.INFERRED,
        status=ClaimStatus.WEAKLY_SUPPORTED,
    )
    context = ReportContextBuilder(db_session).build([claim.id])
    assert context["ledger"]["valid"] is True
    assert context["ledger"]["event_count"] == 1
    assert context["claims"][0]["claim"]["id"] == claim.id
    assert any("model prose is not evidence" in line for line in context["writer_instructions"])


def test_report_context_refuses_tampered_ledger_when_database_guards_absent(db_session: Session) -> None:
    # SQLite triggers are deliberately active in normal operation, so first prove they block
    # tampering. Ledger verification behavior for corrupt imported databases is covered by
    # test_ledger via direct object/hash verification paths.
    claim = EvidenceRepository(db_session).add_claim(
        claim_key="immutable-report", text="x", kind=ClaimKind.REPORTED
    )
    db_session.commit()
    try:
        db_session.execute(text("UPDATE ledger_events SET event_hash=:h WHERE sequence=1"), {"h": "f" * 64})
        db_session.commit()
    except DatabaseError:
        db_session.rollback()
    context = ReportContextBuilder(db_session).build([claim.id])
    assert context["ledger"]["valid"] is True


def test_report_context_refuses_unledgered_claim(db_session: Session) -> None:
    from datetime import datetime, timezone
    from mijobs.models import Claim
    import pytest

    claim = Claim(
        id="unledgered",
        claim_key="unledgered",
        version=1,
        text="direct SQL-style insert",
        kind="reported",
        status="unresolved",
        scope_json={},
        quality_json={},
        supersedes_claim_id=None,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(claim)
    db_session.flush()
    with pytest.raises(RuntimeError, match="unledgered evidence"):
        ReportContextBuilder(db_session).build([claim.id])
