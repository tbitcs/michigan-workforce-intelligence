from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mijobs.domain import ChallengeStatus
from mijobs.models import (
    Challenge,
    Claim,
    DerivedMetricRecord,
    EvidenceEdge,
    Observation,
    SourceArtifact,
)


class EpistemicService:
    def __init__(self, session: Session):
        self.session = session

    def effective_status(self, claim: Claim) -> str:
        latest_by_key: dict[str, Challenge] = {}
        challenges = self.session.scalars(
            select(Challenge)
            .where(Challenge.claim_id == claim.id)
            .order_by(Challenge.challenge_key, Challenge.version.desc())
        )
        for challenge in challenges:
            latest_by_key.setdefault(challenge.challenge_key, challenge)
        if any(ch.status == ChallengeStatus.OPEN.value for ch in latest_by_key.values()):
            return "contested"
        return claim.status

    def trace_claim(self, claim_id: str) -> dict[str, Any]:
        claim = self.session.get(Claim, claim_id)
        if claim is None:
            raise KeyError(f"claim not found: {claim_id}")
        edges = list(
            self.session.scalars(
                select(EvidenceEdge)
                .where(EvidenceEdge.claim_id == claim_id)
                .order_by(EvidenceEdge.created_at, EvidenceEdge.id)
            )
        )
        evidence: list[dict[str, Any]] = []
        artifact_ids: set[str] = set()
        for edge in edges:
            record: dict[str, Any] = {
                "edge_id": edge.id,
                "relation": edge.relation,
                "evidence_type": edge.evidence_type,
                "evidence_id": edge.evidence_id,
                "rationale": edge.rationale,
            }
            if edge.evidence_type == "observation":
                observation = self.session.get(Observation, edge.evidence_id)
                if observation is not None:
                    artifact_ids.add(observation.source_artifact_id)
                    record["observation"] = {
                        "observation_key": observation.observation_key,
                        "version": observation.version,
                        "metric": observation.metric,
                        "value_text": observation.value_text,
                        "numeric_value": observation.numeric_value,
                        "unit": observation.unit,
                        "geography_code": observation.geography_code,
                        "period_start": observation.period_start,
                        "period_end": observation.period_end,
                        "taxonomy_system": observation.taxonomy_system,
                        "taxonomy_version": observation.taxonomy_version,
                        "taxonomy_code": observation.taxonomy_code,
                        "source_artifact_id": observation.source_artifact_id,
                    }
            elif edge.evidence_type == "artifact":
                artifact_ids.add(edge.evidence_id)
            elif edge.evidence_type == "claim":
                supporting_claim = self.session.get(Claim, edge.evidence_id)
                if supporting_claim is not None:
                    record["claim"] = {
                        "claim_key": supporting_claim.claim_key,
                        "version": supporting_claim.version,
                        "text": supporting_claim.text,
                        "status": self.effective_status(supporting_claim),
                    }
            elif edge.evidence_type == "derived_metric":
                derived = self.session.get(DerivedMetricRecord, edge.evidence_id)
                if derived is not None:
                    record["derived_metric"] = {
                        "id": derived.id,
                        "derivation_key": derived.derivation_key,
                        "version": derived.version,
                        "formula_name": derived.formula_name,
                        "formula_version": derived.formula_version,
                        "metric": derived.metric,
                        "numeric_value": derived.numeric_value,
                        "value_text": derived.value_text,
                        "unit": derived.unit,
                        "input_refs": derived.input_refs_json,
                        "scope": derived.scope_json,
                        "assumptions": derived.assumptions_json,
                        "caveats": derived.caveats_json,
                    }
                    for input_ref in derived.input_refs_json:
                        if input_ref.get("type") == "observation":
                            input_observation = self.session.get(Observation, input_ref.get("id"))
                            if input_observation is not None:
                                artifact_ids.add(input_observation.source_artifact_id)
            evidence.append(record)

        artifacts: list[dict[str, Any]] = []
        for artifact_id in sorted(artifact_ids):
            artifact = self.session.get(SourceArtifact, artifact_id)
            if artifact is not None:
                artifacts.append(
                    {
                        "id": artifact.id,
                        "source_id": artifact.source_id,
                        "source_locator": artifact.source_locator,
                        "retrieved_at": artifact.retrieved_at,
                        "content_sha256": artifact.content_sha256,
                        "dataset_version": artifact.dataset_version,
                        "parser_version": artifact.parser_version,
                    }
                )

        challenges = list(
            self.session.scalars(
                select(Challenge)
                .where(Challenge.claim_id == claim_id)
                .order_by(Challenge.challenge_key, Challenge.version)
            )
        )
        return {
            "claim": {
                "id": claim.id,
                "claim_key": claim.claim_key,
                "version": claim.version,
                "text": claim.text,
                "kind": claim.kind,
                "asserted_status": claim.status,
                "effective_status": self.effective_status(claim),
                "scope": claim.scope_json,
                "quality": claim.quality_json,
                "supersedes_claim_id": claim.supersedes_claim_id,
            },
            "evidence": evidence,
            "artifacts": artifacts,
            "challenges": [
                {
                    "id": challenge.id,
                    "challenge_key": challenge.challenge_key,
                    "version": challenge.version,
                    "status": challenge.status,
                    "rationale": challenge.rationale,
                    "challenger_ref": challenge.challenger_ref,
                    "evidence_refs": challenge.evidence_refs_json,
                    "resolution_note": challenge.resolution_note,
                    "supersedes_challenge_id": challenge.supersedes_challenge_id,
                }
                for challenge in challenges
            ],
        }
