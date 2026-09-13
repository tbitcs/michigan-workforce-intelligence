from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mijobs.domain import (
    ChallengeStatus,
    ClaimKind,
    ClaimStatus,
    EvidenceRelation,
    EvidenceType,
    MappingRelation,
    ObservationInput,
    TaxonomyMappingInput,
)
from mijobs.ledger import append_event
from mijobs.models import (
    Challenge,
    Claim,
    DerivedMetricRecord,
    EvidenceEdge,
    LedgerEvent,
    Observation,
    SourceArtifact,
    TaxonomyMapping,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class EvidenceRepository:
    """Append-only persistence API for evidence-bearing entities."""

    def __init__(self, session: Session, *, actor: str = "system"):
        self.session = session
        self.actor = actor

    def add_source_artifact(
        self,
        *,
        source_id: str,
        source_locator: str,
        retrieved_at: datetime,
        content_sha256: str,
        media_type: str,
        byte_size: int,
        local_path: str,
        dataset_version: str | None = None,
        parser_version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SourceArtifact:
        artifact = SourceArtifact(
            id=str(uuid4()),
            source_id=source_id,
            source_locator=source_locator,
            retrieved_at=retrieved_at,
            content_sha256=content_sha256,
            media_type=media_type,
            byte_size=byte_size,
            local_path=local_path,
            dataset_version=dataset_version,
            parser_version=parser_version,
            metadata_json=metadata or {},
            created_at=utcnow(),
        )
        self.session.add(artifact)
        self.session.flush()
        append_event(
            self.session,
            event_type="source_artifact.recorded",
            entity_type="source_artifact",
            entity_id=artifact.id,
            actor=self.actor,
            payload={
                "source_id": artifact.source_id,
                "source_locator": artifact.source_locator,
                "retrieved_at": artifact.retrieved_at,
                "content_sha256": artifact.content_sha256,
                "media_type": artifact.media_type,
                "byte_size": artifact.byte_size,
                "local_path": artifact.local_path,
                "dataset_version": artifact.dataset_version,
                "parser_version": artifact.parser_version,
                "metadata": artifact.metadata_json,
            },
        )
        return artifact

    def add_observation(self, source_artifact_id: str, item: ObservationInput) -> Observation:
        current = self.session.scalar(
            select(Observation)
            .where(Observation.observation_key == item.observation_key)
            .order_by(Observation.version.desc())
            .limit(1)
        )
        version = 1 if current is None else current.version + 1
        observation = Observation(
            id=str(uuid4()),
            observation_key=item.observation_key,
            version=version,
            source_artifact_id=source_artifact_id,
            metric=item.metric,
            value_text=item.value_text,
            numeric_value=float(item.numeric_value) if item.numeric_value is not None else None,
            unit=item.unit,
            geography_type=item.geography_type,
            geography_code=item.geography_code,
            geography_name=item.geography_name,
            period_start=item.period_start,
            period_end=item.period_end,
            period_basis=item.period_basis,
            taxonomy_system=item.taxonomy_system,
            taxonomy_version=item.taxonomy_version,
            taxonomy_code=item.taxonomy_code,
            adjustment=item.adjustment,
            release_status=item.release_status,
            uncertainty_json=item.uncertainty,
            metadata_json=item.metadata,
            supersedes_observation_id=current.id if current else None,
            created_at=utcnow(),
        )
        self.session.add(observation)
        self.session.flush()
        append_event(
            self.session,
            event_type="observation.recorded" if version == 1 else "observation.revised",
            entity_type="observation",
            entity_id=observation.id,
            actor=self.actor,
            payload={
                "observation_key": observation.observation_key,
                "version": observation.version,
                "source_artifact_id": source_artifact_id,
                "metric": observation.metric,
                "value_text": observation.value_text,
                "numeric_value": observation.numeric_value,
                "unit": observation.unit,
                "geography_type": observation.geography_type,
                "geography_code": observation.geography_code,
                "period_start": observation.period_start,
                "period_end": observation.period_end,
                "period_basis": observation.period_basis,
                "taxonomy_system": observation.taxonomy_system,
                "taxonomy_version": observation.taxonomy_version,
                "taxonomy_code": observation.taxonomy_code,
                "adjustment": observation.adjustment,
                "release_status": observation.release_status,
                "uncertainty": observation.uncertainty_json,
                "metadata": observation.metadata_json,
                "supersedes_observation_id": observation.supersedes_observation_id,
            },
        )
        return observation

    def add_derived_metric(
        self,
        *,
        derivation_key: str,
        formula_name: str,
        formula_version: str,
        metric: str,
        value_text: str,
        unit: str,
        numeric_value: float | None,
        input_refs: list[dict[str, Any]],
        scope: dict[str, Any] | None = None,
        assumptions: list[str] | None = None,
        caveats: list[str] | None = None,
    ) -> DerivedMetricRecord:
        if not input_refs:
            raise ValueError("derived metrics require at least one explicit input reference")
        ref_models = {
            "observation": Observation,
            "claim": Claim,
            "derived_metric": DerivedMetricRecord,
        }
        for ref in input_refs:
            ref_type = ref.get("type")
            ref_id = ref.get("id")
            if ref_type not in ref_models or not ref_id:
                raise ValueError("input_refs require a supported type and non-empty id")
            if self.session.get(ref_models[ref_type], ref_id) is None:
                raise KeyError(f"derived metric input not found: {ref_type}:{ref_id}")
        current = self.session.scalar(
            select(DerivedMetricRecord)
            .where(DerivedMetricRecord.derivation_key == derivation_key)
            .order_by(DerivedMetricRecord.version.desc())
            .limit(1)
        )
        version = 1 if current is None else current.version + 1
        record = DerivedMetricRecord(
            id=str(uuid4()),
            derivation_key=derivation_key,
            version=version,
            formula_name=formula_name,
            formula_version=formula_version,
            metric=metric,
            numeric_value=numeric_value,
            value_text=value_text,
            unit=unit,
            input_refs_json=input_refs,
            scope_json=scope or {},
            assumptions_json=assumptions or [],
            caveats_json=caveats or [],
            supersedes_derived_metric_id=current.id if current else None,
            created_at=utcnow(),
        )
        self.session.add(record)
        self.session.flush()
        append_event(
            self.session,
            event_type="derived_metric.recorded" if version == 1 else "derived_metric.revised",
            entity_type="derived_metric",
            entity_id=record.id,
            actor=self.actor,
            payload={
                "derivation_key": record.derivation_key,
                "version": record.version,
                "formula_name": record.formula_name,
                "formula_version": record.formula_version,
                "metric": record.metric,
                "numeric_value": record.numeric_value,
                "value_text": record.value_text,
                "unit": record.unit,
                "input_refs": record.input_refs_json,
                "scope": record.scope_json,
                "assumptions": record.assumptions_json,
                "caveats": record.caveats_json,
                "supersedes_derived_metric_id": record.supersedes_derived_metric_id,
            },
        )
        return record

    def latest_derived_metric(self, derivation_key: str) -> DerivedMetricRecord | None:
        return self.session.scalar(
            select(DerivedMetricRecord)
            .where(DerivedMetricRecord.derivation_key == derivation_key)
            .order_by(DerivedMetricRecord.version.desc())
            .limit(1)
        )

    def add_taxonomy_mapping(
        self,
        *,
        mapping_key: str,
        source_artifact_id: str,
        from_system: str,
        from_version: str,
        from_code: str,
        to_system: str,
        to_version: str,
        to_code: str,
        relation: MappingRelation = MappingRelation.RELATED,
        weight: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaxonomyMapping:
        if self.session.get(SourceArtifact, source_artifact_id) is None:
            raise KeyError(f"source artifact not found: {source_artifact_id}")
        if weight is not None and not 0.0 <= weight <= 1.0:
            raise ValueError("mapping weight must be in [0,1]")
        current = self.session.scalar(
            select(TaxonomyMapping)
            .where(TaxonomyMapping.mapping_key == mapping_key)
            .order_by(TaxonomyMapping.version.desc())
            .limit(1)
        )
        version = 1 if current is None else current.version + 1
        mapping = TaxonomyMapping(
            id=str(uuid4()),
            mapping_key=mapping_key,
            version=version,
            source_artifact_id=source_artifact_id,
            from_system=from_system,
            from_version=from_version,
            from_code=from_code,
            to_system=to_system,
            to_version=to_version,
            to_code=to_code,
            relation=relation.value,
            weight=weight,
            metadata_json=metadata or {},
            supersedes_mapping_id=current.id if current else None,
            created_at=utcnow(),
        )
        self.session.add(mapping)
        self.session.flush()
        append_event(
            self.session,
            event_type="taxonomy_mapping.recorded" if version == 1 else "taxonomy_mapping.revised",
            entity_type="taxonomy_mapping",
            entity_id=mapping.id,
            actor=self.actor,
            payload={
                "mapping_key": mapping.mapping_key,
                "version": mapping.version,
                "source_artifact_id": mapping.source_artifact_id,
                "from_system": mapping.from_system,
                "from_version": mapping.from_version,
                "from_code": mapping.from_code,
                "to_system": mapping.to_system,
                "to_version": mapping.to_version,
                "to_code": mapping.to_code,
                "relation": mapping.relation,
                "weight": mapping.weight,
                "metadata": mapping.metadata_json,
                "supersedes_mapping_id": mapping.supersedes_mapping_id,
            },
        )
        return mapping

    def add_taxonomy_mapping_input(
        self, source_artifact_id: str, item: TaxonomyMappingInput
    ) -> TaxonomyMapping:
        return self.add_taxonomy_mapping(
            mapping_key=item.mapping_key,
            source_artifact_id=source_artifact_id,
            from_system=item.from_system,
            from_version=item.from_version,
            from_code=item.from_code,
            to_system=item.to_system,
            to_version=item.to_version,
            to_code=item.to_code,
            relation=item.relation,
            weight=item.weight,
            metadata=item.metadata,
        )

    def latest_taxonomy_mapping(self, mapping_key: str) -> TaxonomyMapping | None:
        return self.session.scalar(
            select(TaxonomyMapping)
            .where(TaxonomyMapping.mapping_key == mapping_key)
            .order_by(TaxonomyMapping.version.desc())
            .limit(1)
        )

    def add_claim(
        self,
        *,
        claim_key: str,
        text: str,
        kind: ClaimKind,
        status: ClaimStatus = ClaimStatus.UNRESOLVED,
        scope: dict[str, Any] | None = None,
        quality: dict[str, Any] | None = None,
    ) -> Claim:
        current = self.session.scalar(
            select(Claim)
            .where(Claim.claim_key == claim_key)
            .order_by(Claim.version.desc())
            .limit(1)
        )
        version = 1 if current is None else current.version + 1
        claim = Claim(
            id=str(uuid4()),
            claim_key=claim_key,
            version=version,
            text=text,
            kind=kind.value,
            status=status.value,
            scope_json=scope or {},
            quality_json=quality or {},
            supersedes_claim_id=current.id if current else None,
            created_at=utcnow(),
        )
        self.session.add(claim)
        self.session.flush()
        append_event(
            self.session,
            event_type="claim.asserted" if version == 1 else "claim.revised",
            entity_type="claim",
            entity_id=claim.id,
            actor=self.actor,
            payload={
                "claim_key": claim.claim_key,
                "version": claim.version,
                "text": claim.text,
                "kind": claim.kind,
                "status": claim.status,
                "scope": claim.scope_json,
                "quality": claim.quality_json,
                "supersedes_claim_id": claim.supersedes_claim_id,
            },
        )
        return claim

    def add_evidence(
        self,
        *,
        claim_id: str,
        evidence_type: EvidenceType,
        evidence_id: str,
        relation: EvidenceRelation,
        rationale: str | None = None,
    ) -> EvidenceEdge:
        if self.session.get(Claim, claim_id) is None:
            raise KeyError(f"claim not found: {claim_id}")
        evidence_models = {
            EvidenceType.OBSERVATION: Observation,
            EvidenceType.CLAIM: Claim,
            EvidenceType.ARTIFACT: SourceArtifact,
            EvidenceType.DERIVED_METRIC: DerivedMetricRecord,
        }
        if self.session.get(evidence_models[evidence_type], evidence_id) is None:
            raise KeyError(f"evidence not found: {evidence_type.value}:{evidence_id}")
        edge = EvidenceEdge(
            id=str(uuid4()),
            claim_id=claim_id,
            evidence_type=evidence_type.value,
            evidence_id=evidence_id,
            relation=relation.value,
            rationale=rationale,
            created_at=utcnow(),
        )
        self.session.add(edge)
        self.session.flush()
        append_event(
            self.session,
            event_type="evidence.attached",
            entity_type="evidence_edge",
            entity_id=edge.id,
            actor=self.actor,
            payload={
                "claim_id": claim_id,
                "evidence_type": edge.evidence_type,
                "evidence_id": edge.evidence_id,
                "relation": edge.relation,
                "rationale": edge.rationale,
            },
        )
        return edge

    def add_challenge(
        self,
        *,
        claim_id: str,
        rationale: str,
        challenger_ref: str | None = None,
        evidence_refs: list[dict[str, str]] | None = None,
        challenge_key: str | None = None,
    ) -> Challenge:
        if self.session.get(Claim, claim_id) is None:
            raise KeyError(f"claim not found: {claim_id}")
        key = challenge_key or f"challenge:{claim_id}:{uuid4()}"
        challenge = Challenge(
            id=str(uuid4()),
            challenge_key=key,
            version=1,
            claim_id=claim_id,
            status=ChallengeStatus.OPEN.value,
            rationale=rationale,
            challenger_ref=challenger_ref,
            evidence_refs_json=evidence_refs or [],
            resolution_note=None,
            supersedes_challenge_id=None,
            created_at=utcnow(),
        )
        self.session.add(challenge)
        self.session.flush()
        self._ledger_challenge(challenge, "challenge.opened")
        return challenge

    def revise_challenge(
        self,
        *,
        challenge_key: str,
        status: ChallengeStatus,
        resolution_note: str | None = None,
        rationale: str | None = None,
    ) -> Challenge:
        current = self.session.scalar(
            select(Challenge)
            .where(Challenge.challenge_key == challenge_key)
            .order_by(Challenge.version.desc())
            .limit(1)
        )
        if current is None:
            raise KeyError(f"challenge not found: {challenge_key}")
        revised = Challenge(
            id=str(uuid4()),
            challenge_key=current.challenge_key,
            version=current.version + 1,
            claim_id=current.claim_id,
            status=status.value,
            rationale=rationale or current.rationale,
            challenger_ref=current.challenger_ref,
            evidence_refs_json=current.evidence_refs_json,
            resolution_note=resolution_note,
            supersedes_challenge_id=current.id,
            created_at=utcnow(),
        )
        self.session.add(revised)
        self.session.flush()
        self._ledger_challenge(revised, "challenge.revised")
        return revised

    def _ledger_challenge(self, challenge: Challenge, event_type: str) -> None:
        append_event(
            self.session,
            event_type=event_type,
            entity_type="challenge",
            entity_id=challenge.id,
            actor=self.actor,
            payload={
                "challenge_key": challenge.challenge_key,
                "version": challenge.version,
                "claim_id": challenge.claim_id,
                "status": challenge.status,
                "rationale": challenge.rationale,
                "challenger_ref": challenge.challenger_ref,
                "evidence_refs": challenge.evidence_refs_json,
                "resolution_note": challenge.resolution_note,
                "supersedes_challenge_id": challenge.supersedes_challenge_id,
            },
        )

    def latest_claim(self, claim_key: str) -> Claim | None:
        return self.session.scalar(
            select(Claim)
            .where(Claim.claim_key == claim_key)
            .order_by(Claim.version.desc())
            .limit(1)
        )

    def latest_observation(self, observation_key: str) -> Observation | None:
        return self.session.scalar(
            select(Observation)
            .where(Observation.observation_key == observation_key)
            .order_by(Observation.version.desc())
            .limit(1)
        )

    def claim_challenges(self, claim_id: str, *, latest_only: bool = True) -> list[Challenge]:
        challenges = list(
            self.session.scalars(
                select(Challenge)
                .where(Challenge.claim_id == claim_id)
                .order_by(Challenge.challenge_key, Challenge.version.desc())
            )
        )
        if not latest_only:
            return challenges
        seen: set[str] = set()
        latest: list[Challenge] = []
        for challenge in challenges:
            if challenge.challenge_key not in seen:
                seen.add(challenge.challenge_key)
                latest.append(challenge)
        return latest

    def count_events(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(LedgerEvent)) or 0)
