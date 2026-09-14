from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from mijobs.analytics.gaps import ComparableMetric, market_tightness, training_pipeline_gap
from mijobs.analytics.policy import (
    assumptions_from_mapping,
    evaluate_training_policy_sensitivity,
)
from mijobs.analytics.university import (
    BusinessAttractionInput,
    DegreeRelevanceInput,
    OccupationDemandInput,
    RetentionRiskInput,
    RetentionRiskResult,
    UniversityPipelineResult,
    business_attraction_signal,
    crosswalk_edges_from_mappings,
    degree_relevance,
    retention_risk,
    university_pipeline_balance,
    university_workforce_summary,
)
from mijobs.config import SourceCatalog
from mijobs.epistemics import EpistemicService
from mijobs.ledger import audit_evidence_coverage, verify_ledger
from mijobs.models import Claim, Observation, SourceArtifact, TaxonomyMapping
from mijobs.reporting import ReportContextBuilder
from mijobs.repository import EvidenceRepository
from mijobs.sources.institutions import PARTNER_INSTITUTIONS, get_partner_institution


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
        return {
            "chain": asdict(chain),
            "coverage": asdict(coverage),
            "valid": chain.valid and coverage.valid,
        }

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

    def university_degree_relevance(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Match a candidate institution's CIP completions to in-demand SOC occupations.

        Required payload keys:
          - institution_unitid: IPEDS UnitID of the candidate institution
          - completions: list of {cip_code, annual_completions, cip_version?}
          - demand: list of {soc_code, annual_openings, soc_version?, median_wage?}
          - crosswalk: list of {from_code, to_code, from_version?, to_version?, relation?}
        """
        unitid = payload.get("institution_unitid")
        if not unitid:
            raise ValueError("institution_unitid is required")
        institution = get_partner_institution(unitid)
        if institution is None:
            raise ValueError(
                f"institution_unitid {unitid!r} is not a registered candidate institution"
            )

        completions_raw = payload.get("completions", [])
        if not completions_raw:
            raise ValueError("completions list is required and must be non-empty")
        completions = [
            DegreeRelevanceInput(
                institution_unitid=unitid,
                cip_code=c["cip_code"],
                cip_version=c.get("cip_version", "2020"),
                annual_completions=Decimal(str(c["annual_completions"])),
            )
            for c in completions_raw
        ]

        demand_raw = payload.get("demand", [])
        if not demand_raw:
            raise ValueError("demand list is required and must be non-empty")
        demand = [
            OccupationDemandInput(
                soc_code=d["soc_code"],
                soc_version=d.get("soc_version", "2018"),
                annual_openings=Decimal(str(d["annual_openings"])),
                geography_code=d.get("geography_code", "MI"),
                median_wage=Decimal(str(d["median_wage"])) if d.get("median_wage") else None,
            )
            for d in demand_raw
        ]

        crosswalk_raw = payload.get("crosswalk", [])
        if not crosswalk_raw:
            raise ValueError("crosswalk list is required and must be non-empty")
        crosswalk = crosswalk_edges_from_mappings(crosswalk_raw)

        result = degree_relevance(
            institution=institution,
            completions=completions,
            demand=demand,
            crosswalk=crosswalk,
        )
        return _jsonable_dict(asdict(result))

    def university_pipeline_balance(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Compute net pipeline surplus/deficit for a candidate institution.

        Same payload structure as university_degree_relevance.
        """
        unitid = payload.get("institution_unitid")
        if not unitid:
            raise ValueError("institution_unitid is required")
        institution = get_partner_institution(unitid)
        if institution is None:
            raise ValueError(
                f"institution_unitid {unitid!r} is not a registered candidate institution"
            )

        completions_raw = payload.get("completions", [])
        if not completions_raw:
            raise ValueError("completions list is required and must be non-empty")
        completions = [
            DegreeRelevanceInput(
                institution_unitid=unitid,
                cip_code=c["cip_code"],
                cip_version=c.get("cip_version", "2020"),
                annual_completions=Decimal(str(c["annual_completions"])),
            )
            for c in completions_raw
        ]

        demand_raw = payload.get("demand", [])
        if not demand_raw:
            raise ValueError("demand list is required and must be non-empty")
        demand = [
            OccupationDemandInput(
                soc_code=d["soc_code"],
                soc_version=d.get("soc_version", "2018"),
                annual_openings=Decimal(str(d["annual_openings"])),
                geography_code=d.get("geography_code", "MI"),
            )
            for d in demand_raw
        ]

        crosswalk_raw = payload.get("crosswalk", [])
        if not crosswalk_raw:
            raise ValueError("crosswalk list is required and must be non-empty")
        crosswalk = crosswalk_edges_from_mappings(crosswalk_raw)

        result = university_pipeline_balance(
            institution=institution,
            completions=completions,
            demand=demand,
            crosswalk=crosswalk,
        )
        return _jsonable_dict(asdict(result))

    def university_retention_risk(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Estimate graduate retention risk for a candidate institution.

        Required payload keys:
          - institution_unitid: IPEDS UnitID
          - annual_graduates: total graduates
          - michigan_resident_share: fraction [0,1]
          - in_state_job_match_rate: fraction [0,1]
          - out_migration_rate: fraction [0,1]
        """
        unitid = payload.get("institution_unitid")
        if not unitid:
            raise ValueError("institution_unitid is required")
        institution = get_partner_institution(unitid)
        if institution is None:
            raise ValueError(
                f"institution_unitid {unitid!r} is not a registered candidate institution"
            )

        inputs = RetentionRiskInput(
            annual_graduates=Decimal(str(payload["annual_graduates"])),
            michigan_resident_share=Decimal(str(payload["michigan_resident_share"])),
            in_state_job_match_rate=Decimal(str(payload["in_state_job_match_rate"])),
            out_migration_rate=Decimal(str(payload["out_migration_rate"])),
        )
        result = retention_risk(institution=institution, inputs=inputs)
        return _jsonable_dict(asdict(result))

    def business_attraction(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Evaluate out-of-state business attraction potential for a target industry.

        Required payload keys:
          - target_industry_naics: NAICS code
          - current_establishments, projected_establishments_5yr
          - current_employment, projected_employment_5yr
          - target_occupations: list of {soc_code, annual_openings}
          - median_wage_target, median_wage_michigan (optional)
        """
        target_occupations = [
            OccupationDemandInput(
                soc_code=d["soc_code"],
                soc_version=d.get("soc_version", "2018"),
                annual_openings=Decimal(str(d["annual_openings"])),
                geography_code=d.get("geography_code", "MI"),
            )
            for d in payload.get("target_occupations", [])
        ]
        inputs = BusinessAttractionInput(
            target_industry_naics=payload["target_industry_naics"],
            target_occupations=tuple(target_occupations),
            current_establishments=Decimal(str(payload["current_establishments"])),
            projected_establishments_5yr=Decimal(str(payload["projected_establishments_5yr"])),
            current_employment=Decimal(str(payload["current_employment"])),
            projected_employment_5yr=Decimal(str(payload["projected_employment_5yr"])),
            median_wage_target=Decimal(str(payload["median_wage_target"]))
            if payload.get("median_wage_target")
            else None,
            median_wage_michigan=Decimal(str(payload["median_wage_michigan"]))
            if payload.get("median_wage_michigan")
            else None,
        )
        result = business_attraction_signal(inputs=inputs)
        return _jsonable_dict(asdict(result))

    def university_summary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Aggregate workforce pipeline summary across all candidate institutions.

        Optional payload keys:
          - pipeline_results: list of results from university_pipeline_balance
          - retention_results: list of results from university_retention_risk
        """
        payload = payload or {}
        pipeline_results_raw = payload.get("pipeline_results", [])
        if not pipeline_results_raw:
            raise ValueError("pipeline_results list is required and must be non-empty")

        pipeline_results = [
            UniversityPipelineResult(
                formula_version=r.get("formula_version", "university_pipeline_balance/v1"),
                institution_unitid=r["institution_unitid"],
                institution_name=r.get("institution_name"),
                total_annual_completions=Decimal(str(r["total_annual_completions"])),
                total_annual_openings_matched=Decimal(str(r["total_annual_openings_matched"])),
                pipeline_surplus=Decimal(str(r.get("pipeline_surplus", "0"))),
                pipeline_deficit=Decimal(str(r.get("pipeline_deficit", "0"))),
                net_balance=Decimal(str(r["net_balance"])),
                classification=r.get("classification", "unknown"),
                focus_areas=tuple(r.get("focus_areas", ())),
                caveats=tuple(r.get("caveats", ())),
            )
            for r in pipeline_results_raw
        ]

        retention_results = None
        retention_raw = payload.get("retention_results")
        if retention_raw:
            retention_results = [
                RetentionRiskResult(
                    formula_version=r.get("formula_version", "retention_risk/v1"),
                    institution_unitid=r["institution_unitid"],
                    institution_name=r.get("institution_name"),
                    annual_graduates=Decimal(str(r["annual_graduates"])),
                    estimated_michigan_retained=Decimal(str(r["estimated_michigan_retained"])),
                    estimated_leaving_michigan=Decimal(str(r["estimated_leaving_michigan"])),
                    retention_rate=Decimal(str(r["retention_rate"])),
                    risk_classification=r.get("risk_classification", "unknown"),
                    caveats=tuple(r.get("caveats", ())),
                )
                for r in retention_raw
            ]

        result = university_workforce_summary(
            institutions=PARTNER_INSTITUTIONS,
            pipeline_results=pipeline_results,
            retention_results=retention_results,
        )
        return _jsonable_dict(asdict(result))

    def partner_institutions_list(self) -> dict[str, Any]:
        """List all registered candidate institutions with their focus areas."""
        return {
            "count": len(PARTNER_INSTITUTIONS),
            "relationship_status": "candidate",
            "additional_candidates": json.loads(
                Path("config/education-candidates.json").read_text(encoding="utf-8")
            ),
            "participation_confirmed": False,
            "limitations": [
                "All institutions are candidates only. Stored outcomes do not establish representation, commitment, capacity, or available workers."
            ],
            "institutions": [
                {
                    "relationship_status": inst.relationship_status,
                    "unitid": inst.unitid,
                    "name": inst.name,
                    "city": inst.city,
                    "state": inst.state,
                    "control": inst.control,
                    "sector": inst.sector,
                    "iclevel": inst.iclevel,
                    "focus_areas": list(inst.focus_areas),
                    "metadata": inst.metadata,
                }
                for inst in PARTNER_INSTITUTIONS
            ],
        }

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
            raise PermissionError(
                "MCP writes are disabled; set MIJOBS_MCP_WRITE_ENABLED=true explicitly"
            )
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
            "period_start": observation.period_start.isoformat()
            if observation.period_start
            else None,
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
