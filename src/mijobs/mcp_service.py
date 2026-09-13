from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from mijobs.analytics.gaps import ComparableMetric, market_tightness, training_pipeline_gap
from mijobs.analytics.policy import (
    assumptions_from_mapping,
    evaluate_training_policy_sensitivity,
)
from mijobs.config import SourceCatalog
from mijobs.epistemics import EpistemicService
from mijobs.ledger import audit_evidence_coverage, verify_ledger
from mijobs.models import Claim, Observation, SourceArtifact, TaxonomyMapping
from mijobs.reporting import ReportContextBuilder
from mijobs.repository import EvidenceRepository


class MCPService:
    """SDK-independent application service used by the MCP transport and unit tests."""

    MAX_QUERY_LIMIT = 500

    def __init__(self, session: Session, catalog: SourceCatalog, *, write_enabled: bool = False):
        self.session = session
        self.catalog = catalog
        self.write_enabled = write_enabled

    def sources_list(self) -> dict[str, Any]:
        return {
            "schema_version": self.catalog.schema_version,
            "reviewed_at": self.catalog.reviewed_at,
            "sources": [source.model_dump(mode="json") for source in self.catalog.sources],
        }

    def observations_search(
        self,
        *,
        metric: str | None = None,
        geography_code: str | None = None,
        taxonomy_code: str | None = None,
        source_artifact_id: str | None = None,
        latest_only: bool = True,
        limit: int = 100,
    ) -> dict[str, Any]:
        limit = self._checked_limit(limit)
        stmt = select(Observation)
        if latest_only:
            newer = aliased(Observation)
            stmt = stmt.where(
                ~select(newer.id)
                .where(
                    newer.observation_key == Observation.observation_key,
                    newer.version > Observation.version,
                )
                .exists()
            )
        if metric is not None:
            stmt = stmt.where(Observation.metric == metric)
        if geography_code is not None:
            stmt = stmt.where(Observation.geography_code == geography_code)
        if taxonomy_code is not None:
            stmt = stmt.where(Observation.taxonomy_code == taxonomy_code)
        if source_artifact_id is not None:
            stmt = stmt.where(Observation.source_artifact_id == source_artifact_id)
        stmt = stmt.order_by(Observation.created_at.desc(), Observation.id).limit(limit)
        rows = list(self.session.scalars(stmt))
        return {
            "count": len(rows),
            "latest_only": latest_only,
            "limit": limit,
            "observations": [self._observation_dict(row) for row in rows],
        }

    def artifacts_get(self, artifact_id: str) -> dict[str, Any]:
        artifact = self.session.get(SourceArtifact, artifact_id)
        if artifact is None:
            raise KeyError(artifact_id)
        return {
            "id": artifact.id,
            "source_id": artifact.source_id,
            "source_locator": artifact.source_locator,
            "retrieved_at": artifact.retrieved_at.isoformat(),
            "content_sha256": artifact.content_sha256,
            "media_type": artifact.media_type,
            "byte_size": artifact.byte_size,
            "local_path": artifact.local_path,
            "dataset_version": artifact.dataset_version,
            "parser_version": artifact.parser_version,
            "metadata": artifact.metadata_json,
        }

    def claims_search(
        self,
        *,
        kind: str | None = None,
        asserted_status: str | None = None,
        latest_only: bool = True,
        limit: int = 100,
    ) -> dict[str, Any]:
        limit = self._checked_limit(limit)
        stmt = select(Claim)
        if latest_only:
            newer = aliased(Claim)
            stmt = stmt.where(
                ~select(newer.id)
                .where(newer.claim_key == Claim.claim_key, newer.version > Claim.version)
                .exists()
            )
        if kind is not None:
            stmt = stmt.where(Claim.kind == kind)
        if asserted_status is not None:
            stmt = stmt.where(Claim.status == asserted_status)
        stmt = stmt.order_by(Claim.created_at.desc(), Claim.id).limit(limit)
        claims = list(self.session.scalars(stmt))
        epistemics = EpistemicService(self.session)
        return {
            "count": len(claims),
            "latest_only": latest_only,
            "limit": limit,
            "claims": [
                {
                    "id": claim.id,
                    "claim_key": claim.claim_key,
                    "version": claim.version,
                    "text": claim.text,
                    "kind": claim.kind,
                    "asserted_status": claim.status,
                    "effective_status": epistemics.effective_status(claim),
                    "scope": claim.scope_json,
                    "quality": claim.quality_json,
                    "created_at": claim.created_at.isoformat(),
                }
                for claim in claims
            ],
        }

    def mappings_search(
        self,
        *,
        from_system: str | None = None,
        from_code: str | None = None,
        to_system: str | None = None,
        to_code: str | None = None,
        latest_only: bool = True,
        limit: int = 100,
    ) -> dict[str, Any]:
        limit = self._checked_limit(limit)
        stmt = select(TaxonomyMapping)
        if latest_only:
            newer = aliased(TaxonomyMapping)
            stmt = stmt.where(
                ~select(newer.id)
                .where(
                    newer.mapping_key == TaxonomyMapping.mapping_key,
                    newer.version > TaxonomyMapping.version,
                )
                .exists()
            )
        if from_system is not None:
            stmt = stmt.where(TaxonomyMapping.from_system == from_system)
        if from_code is not None:
            stmt = stmt.where(TaxonomyMapping.from_code == from_code)
        if to_system is not None:
            stmt = stmt.where(TaxonomyMapping.to_system == to_system)
        if to_code is not None:
            stmt = stmt.where(TaxonomyMapping.to_code == to_code)
        stmt = stmt.order_by(TaxonomyMapping.created_at.desc(), TaxonomyMapping.id).limit(limit)
        mappings = list(self.session.scalars(stmt))
        return {
            "count": len(mappings),
            "latest_only": latest_only,
            "limit": limit,
            "mappings": [
                {
                    "id": item.id,
                    "mapping_key": item.mapping_key,
                    "version": item.version,
                    "source_artifact_id": item.source_artifact_id,
                    "from_system": item.from_system,
                    "from_version": item.from_version,
                    "from_code": item.from_code,
                    "to_system": item.to_system,
                    "to_version": item.to_version,
                    "to_code": item.to_code,
                    "relation": item.relation,
                    "weight": item.weight,
                    "metadata": item.metadata_json,
                    "supersedes_mapping_id": item.supersedes_mapping_id,
                }
                for item in mappings
            ],
        }

    def claims_get(self, claim_id: str) -> dict[str, Any]:
        claim = self.session.get(Claim, claim_id)
        if claim is None:
            raise KeyError(claim_id)
        status = EpistemicService(self.session).effective_status(claim)
        return {
            "id": claim.id,
            "claim_key": claim.claim_key,
            "version": claim.version,
            "text": claim.text,
            "kind": claim.kind,
            "asserted_status": claim.status,
            "effective_status": status,
            "scope": claim.scope_json,
            "quality": claim.quality_json,
        }

    def claims_trace(self, claim_id: str) -> dict[str, Any]:
        return EpistemicService(self.session).trace_claim(claim_id)

    def ledger_verify(self) -> dict[str, Any]:
        return asdict(verify_ledger(self.session))

    def ledger_audit(self) -> dict[str, Any]:
        chain = verify_ledger(self.session)
        coverage = audit_evidence_coverage(self.session)
        return {"chain": asdict(chain), "coverage": asdict(coverage), "valid": chain.valid and coverage.valid}

    def gap_training_pipeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        def metric(name: str) -> ComparableMetric | None:
            raw = payload.get(name)
            if raw is None:
                return None
            return ComparableMetric(
                name=name,
                value=Decimal(str(raw["value"])),
                unit=raw["unit"],
                geography_code=raw["geography_code"],
                period_basis=raw["period_basis"],
                taxonomy_system=raw["taxonomy_system"],
                taxonomy_version=raw["taxonomy_version"],
                taxonomy_code=raw["taxonomy_code"],
                source_observation_id=raw.get("source_observation_id"),
            )

        annual_openings = metric("annual_openings")
        completions = metric("completions")
        if annual_openings is None or completions is None:
            raise ValueError("annual_openings and completions are required")
        result = training_pipeline_gap(
            annual_openings=annual_openings,
            completions=completions,
            apprenticeship_completions=metric("apprenticeship_completions"),
            estimated_transfers_in=metric("estimated_transfers_in"),
            other_known_supply=metric("other_known_supply"),
        )
        response = asdict(result)
        return _jsonable_dict(response)

    def gap_market_tightness(self, online_job_ads: str, available_people: str) -> dict[str, Any]:
        result = market_tightness(
            online_job_ads=Decimal(online_job_ads), available_people=Decimal(available_people)
        )
        return _jsonable_dict(asdict(result))

    def policy_training_scenario(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Evaluate caller-supplied low/base/high workforce-policy assumptions."""
        if "baseline_gap_workers" not in payload:
            raise ValueError("baseline_gap_workers is required")
        for name in ("low", "base", "high"):
            if name not in payload or not isinstance(payload[name], dict):
                raise ValueError(f"{name} assumption set is required")
        result = evaluate_training_policy_sensitivity(
            baseline_gap_workers=Decimal(str(payload["baseline_gap_workers"])),
            low=assumptions_from_mapping(payload["low"]),
            base=assumptions_from_mapping(payload["base"]),
            high=assumptions_from_mapping(payload["high"]),
        )
        return _jsonable_dict(asdict(result))

    def report_context(self, claim_ids: list[str]) -> dict[str, Any]:
        return ReportContextBuilder(self.session).build(claim_ids)

    def claims_challenge(
        self,
        *,
        claim_id: str,
        rationale: str,
        challenger_ref: str | None = None,
        evidence_refs: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if not self.write_enabled:
            raise PermissionError("MCP writes are disabled; set MIJOBS_MCP_WRITE_ENABLED=true explicitly")
        challenge = EvidenceRepository(self.session, actor="mcp").add_challenge(
            claim_id=claim_id,
            rationale=rationale,
            challenger_ref=challenger_ref,
            evidence_refs=evidence_refs,
        )
        self.session.commit()
        return {
            "id": challenge.id,
            "challenge_key": challenge.challenge_key,
            "version": challenge.version,
            "status": challenge.status,
        }

    @classmethod
    def _checked_limit(cls, limit: int) -> int:
        if not 1 <= limit <= cls.MAX_QUERY_LIMIT:
            raise ValueError(f"limit must be in [1,{cls.MAX_QUERY_LIMIT}]")
        return limit

    @staticmethod
    def _observation_dict(observation: Observation) -> dict[str, Any]:
        return {
            "id": observation.id,
            "observation_key": observation.observation_key,
            "version": observation.version,
            "source_artifact_id": observation.source_artifact_id,
            "metric": observation.metric,
            "value_text": observation.value_text,
            "numeric_value": observation.numeric_value,
            "unit": observation.unit,
            "geography_type": observation.geography_type,
            "geography_code": observation.geography_code,
            "geography_name": observation.geography_name,
            "period_start": observation.period_start.isoformat() if observation.period_start else None,
            "period_end": observation.period_end.isoformat() if observation.period_end else None,
            "period_basis": observation.period_basis,
            "taxonomy_system": observation.taxonomy_system,
            "taxonomy_version": observation.taxonomy_version,
            "taxonomy_code": observation.taxonomy_code,
            "adjustment": observation.adjustment,
            "release_status": observation.release_status,
            "uncertainty": observation.uncertainty_json,
            "metadata": observation.metadata_json,
            "supersedes_observation_id": observation.supersedes_observation_id,
            "created_at": observation.created_at.isoformat(),
        }


def _jsonable_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {key: _jsonable_decimal(item) for key, item in value.items()}


def _jsonable_decimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable_decimal(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable_decimal(item) for item in value]
    return value
