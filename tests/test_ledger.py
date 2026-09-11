from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from mijobs.ledger import GENESIS_HASH, append_event, verify_ledger
from mijobs.models import LedgerEvent


def test_empty_ledger_is_valid(db_session: Session) -> None:
    result = verify_ledger(db_session)
    assert result.valid
    assert result.event_count == 0
    assert result.head_hash == GENESIS_HASH


def test_ledger_append_and_verify(db_session: Session) -> None:
    first = append_event(
        db_session,
        event_type="test.created",
        entity_type="test",
        entity_id="a",
        payload={"value": 1},
        actor="pytest",
        occurred_at=datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc),
    )
    second = append_event(
        db_session,
        event_type="test.created",
        entity_type="test",
        entity_id="b",
        payload={"value": 2},
        actor="pytest",
        occurred_at=datetime(2026, 9, 11, 12, 1, tzinfo=timezone.utc),
    )
    assert second.previous_hash == first.event_hash
    result = verify_ledger(db_session)
    assert result.valid
    assert result.event_count == 2
    assert result.head_hash == second.event_hash


def test_database_blocks_ledger_update_and_delete(db_session: Session) -> None:
    event = append_event(
        db_session,
        event_type="test.created",
        entity_type="test",
        entity_id="a",
        payload={"value": 1},
    )
    db_session.commit()
    with pytest.raises(DatabaseError):
        db_session.execute(
            text("UPDATE ledger_events SET payload_hash = :h WHERE sequence = :s"),
            {"h": "f" * 64, "s": event.sequence},
        )
        db_session.commit()
    db_session.rollback()
    with pytest.raises(DatabaseError):
        db_session.execute(text("DELETE FROM ledger_events WHERE sequence = :s"), {"s": event.sequence})
        db_session.commit()
    db_session.rollback()
    assert db_session.get(LedgerEvent, event.sequence) is not None


def test_verifier_detects_payload_tamper_in_imported_database(tmp_path) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from mijobs.models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'unguarded.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        append_event(
            session,
            event_type="test.created",
            entity_type="test",
            entity_id="a",
            payload={"value": 1},
        )
        session.commit()
        session.execute(text("UPDATE ledger_events SET payload_json=:p WHERE sequence=1"), {"p": '{"value":2}'})
        session.commit()
        result = verify_ledger(session)
        assert result.valid is False
        assert result.first_invalid_sequence == 1
        assert result.reason == "payload_hash mismatch"
    engine.dispose()


def test_coverage_audit_detects_unledgered_evidence(db_session: Session) -> None:
    from datetime import datetime, timezone
    from mijobs.ledger import audit_evidence_coverage
    from mijobs.models import Claim

    db_session.add(
        Claim(
            id="direct-insert",
            claim_key="direct",
            version=1,
            text="bypassed repository",
            kind="reported",
            status="unresolved",
            scope_json={},
            quality_json={},
            supersedes_claim_id=None,
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.flush()
    audit = audit_evidence_coverage(db_session)
    assert audit.valid is False
    assert ("claim", "direct-insert") in audit.uncovered
