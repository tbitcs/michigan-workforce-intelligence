from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mijobs.canonical import canonical_json, canonical_sha256
from mijobs.models import LedgerEvent

GENESIS_HASH = "0" * 64
LEDGER_SCHEMA_VERSION = "1"


@dataclass(frozen=True, slots=True)
class LedgerVerification:
    valid: bool
    event_count: int
    head_hash: str
    first_invalid_sequence: int | None = None
    reason: str | None = None


def _header(
    *,
    sequence: int,
    event_id: str,
    stream: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    occurred_at: datetime,
    payload_hash: str,
    previous_hash: str,
    actor: str,
    schema_version: str,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "event_id": event_id,
        "stream": stream,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "occurred_at": occurred_at,
        "payload_hash": payload_hash,
        "previous_hash": previous_hash,
        "actor": actor,
        "schema_version": schema_version,
    }


def append_event(
    session: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
    actor: str = "system",
    stream: str = "global",
    occurred_at: datetime | None = None,
) -> LedgerEvent:
    last = session.scalar(select(LedgerEvent).order_by(LedgerEvent.sequence.desc()).limit(1))
    max_sequence = session.scalar(select(func.max(LedgerEvent.sequence))) or 0
    sequence = int(max_sequence) + 1
    previous_hash = last.event_hash if last is not None else GENESIS_HASH
    timestamp = occurred_at or datetime.now(UTC)
    event_id = str(uuid4())
    canonical_payload = json.loads(canonical_json(payload))
    payload_hash = canonical_sha256(canonical_payload)
    header = _header(
        sequence=sequence,
        event_id=event_id,
        stream=stream,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        occurred_at=timestamp,
        payload_hash=payload_hash,
        previous_hash=previous_hash,
        actor=actor,
        schema_version=LEDGER_SCHEMA_VERSION,
    )
    event_hash = canonical_sha256(header)
    event = LedgerEvent(
        sequence=sequence,
        event_id=event_id,
        stream=stream,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        occurred_at=timestamp,
        payload_json=canonical_payload,
        payload_hash=payload_hash,
        previous_hash=previous_hash,
        event_hash=event_hash,
        actor=actor,
        schema_version=LEDGER_SCHEMA_VERSION,
    )
    session.add(event)
    session.flush()
    return event


def verify_ledger(session: Session) -> LedgerVerification:
    events = list(session.scalars(select(LedgerEvent).order_by(LedgerEvent.sequence)))
    previous = GENESIS_HASH
    expected_sequence = 1
    for event in events:
        if event.sequence != expected_sequence:
            return LedgerVerification(
                False,
                len(events),
                previous,
                event.sequence,
                f"sequence gap: expected {expected_sequence}, got {event.sequence}",
            )
        if event.previous_hash != previous:
            return LedgerVerification(
                False,
                len(events),
                previous,
                event.sequence,
                "previous_hash mismatch",
            )
        expected_payload_hash = canonical_sha256(event.payload_json)
        if event.payload_hash != expected_payload_hash:
            return LedgerVerification(
                False,
                len(events),
                previous,
                event.sequence,
                "payload_hash mismatch",
            )
        expected_event_hash = canonical_sha256(
            _header(
                sequence=event.sequence,
                event_id=event.event_id,
                stream=event.stream,
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                occurred_at=event.occurred_at,
                payload_hash=event.payload_hash,
                previous_hash=event.previous_hash,
                actor=event.actor,
                schema_version=event.schema_version,
            )
        )
        if event.event_hash != expected_event_hash:
            return LedgerVerification(
                False,
                len(events),
                previous,
                event.sequence,
                "event_hash mismatch",
            )
        previous = event.event_hash
        expected_sequence += 1
    return LedgerVerification(True, len(events), previous)


@dataclass(frozen=True, slots=True)
class EvidenceCoverageAudit:
    valid: bool
    checked_entities: int
    uncovered: tuple[tuple[str, str], ...]


def audit_evidence_coverage(session: Session) -> EvidenceCoverageAudit:
    """Verify that every persisted evidence-bearing row has at least one ledger event.

    This closes an important integrity gap: a cryptographically valid event chain is not
    sufficient if application data can exist outside that chain.
    """
    from mijobs.models import (
        Challenge,
        Claim,
        DerivedMetricRecord,
        EvidenceEdge,
        Observation,
        SourceArtifact,
        TaxonomyMapping,
    )

    entity_models = (
        ("source_artifact", SourceArtifact),
        ("observation", Observation),
        ("claim", Claim),
        ("evidence_edge", EvidenceEdge),
        ("challenge", Challenge),
        ("taxonomy_mapping", TaxonomyMapping),
        ("derived_metric", DerivedMetricRecord),
    )
    covered = set(session.execute(select(LedgerEvent.entity_type, LedgerEvent.entity_id)).all())
    uncovered: list[tuple[str, str]] = []
    checked = 0
    for entity_type, model in entity_models:
        ids = list(session.scalars(select(model.id)))
        checked += len(ids)
        for entity_id in ids:
            if (entity_type, entity_id) not in covered:
                uncovered.append((entity_type, entity_id))
    return EvidenceCoverageAudit(
        valid=not uncovered,
        checked_entities=checked,
        uncovered=tuple(sorted(uncovered)),
    )
