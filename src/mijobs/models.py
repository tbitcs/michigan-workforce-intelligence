from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceArtifact(Base):
    __tablename__ = "source_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    source_locator: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    media_type: Mapped[str] = mapped_column(String(128))
    byte_size: Mapped[int] = mapped_column(Integer)
    local_path: Mapped[str] = mapped_column(Text)
    dataset_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("observation_key", "version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    observation_key: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[int] = mapped_column(Integer)
    source_artifact_id: Mapped[str] = mapped_column(ForeignKey("source_artifacts.id"), index=True)
    metric: Mapped[str] = mapped_column(String(255), index=True)
    value_text: Mapped[str] = mapped_column(Text)
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(64))
    geography_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    geography_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geography_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)
    taxonomy_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    taxonomy_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    taxonomy_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    adjustment: Mapped[str | None] = mapped_column(String(64), nullable=True)
    release_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uncertainty_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    supersedes_observation_id: Mapped[str | None] = mapped_column(
        ForeignKey("observations.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (UniqueConstraint("claim_key", "version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_key: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), index=True)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    quality_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    supersedes_claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceEdge(Base):
    __tablename__ = "evidence_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(32))
    evidence_id: Mapped[str] = mapped_column(String(36), index=True)
    relation: Mapped[str] = mapped_column(String(32), index=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Challenge(Base):
    __tablename__ = "challenges"
    __table_args__ = (UniqueConstraint("challenge_key", "version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    challenge_key: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[int] = mapped_column(Integer)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    rationale: Mapped[str] = mapped_column(Text)
    challenger_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_refs_json: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    supersedes_challenge_id: Mapped[str | None] = mapped_column(
        ForeignKey("challenges.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DerivedMetricRecord(Base):
    __tablename__ = "derived_metrics"
    __table_args__ = (UniqueConstraint("derivation_key", "version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    derivation_key: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[int] = mapped_column(Integer)
    formula_name: Mapped[str] = mapped_column(String(128), index=True)
    formula_version: Mapped[str] = mapped_column(String(64))
    metric: Mapped[str] = mapped_column(String(255), index=True)
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(64))
    input_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    assumptions_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    caveats_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    supersedes_derived_metric_id: Mapped[str | None] = mapped_column(
        ForeignKey("derived_metrics.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TaxonomyMapping(Base):
    __tablename__ = "taxonomy_mappings"
    __table_args__ = (UniqueConstraint("mapping_key", "version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mapping_key: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[int] = mapped_column(Integer)
    source_artifact_id: Mapped[str] = mapped_column(ForeignKey("source_artifacts.id"), index=True)
    from_system: Mapped[str] = mapped_column(String(64), index=True)
    from_version: Mapped[str] = mapped_column(String(64))
    from_code: Mapped[str] = mapped_column(String(128), index=True)
    to_system: Mapped[str] = mapped_column(String(64), index=True)
    to_version: Mapped[str] = mapped_column(String(64))
    to_code: Mapped[str] = mapped_column(String(128), index=True)
    relation: Mapped[str] = mapped_column(String(32))
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    supersedes_mapping_id: Mapped[str | None] = mapped_column(
        ForeignKey("taxonomy_mappings.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LedgerEvent(Base):
    __tablename__ = "ledger_events"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    stream: Mapped[str] = mapped_column(String(64), default="global")
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64))
    previous_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)
    actor: Mapped[str] = mapped_column(String(128))
    schema_version: Mapped[str] = mapped_column(String(32), default="1")
