"""University workforce pipeline analytics.

This module computes deterministic, evidence-linked metrics that connect
university degree completions (CIP taxonomy) to labor-market demand (SOC
taxonomy) using the official NCES CIP-to-SOC crosswalk. It also provides
retention-risk and business-attraction signals for Michigan-specific
policy questions.

All metrics are formula-versioned, carry explicit caveats, and refuse
incompatible inputs. No causal parameters are inferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from mijobs.sources.institutions import PARTNER_INSTITUTIONS, PartnerInstitution

ZERO = Decimal("0")
ONE = Decimal("1")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DegreeRelevanceInput:
    """One CIP-code completion count for a single institution and period."""

    institution_unitid: str
    cip_code: str
    cip_version: str
    annual_completions: Decimal
    period_basis: str = "academic_year"
    period_start: str | None = None
    period_end: str | None = None


@dataclass(frozen=True, slots=True)
class OccupationDemandInput:
    """Annual projected openings for one SOC occupation in a target geography."""

    soc_code: str
    soc_version: str
    annual_openings: Decimal
    geography_code: str
    period_basis: str = "annual"
    median_wage: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CrosswalkEdge:
    """A single CIP-to-SOC relationship from the official crosswalk."""

    cip_code: str
    cip_version: str
    soc_code: str
    soc_version: str
    relation: str = "related"
    weight: float | None = None


@dataclass(frozen=True, slots=True)
class DegreeRelevanceResult:
    """Result of matching an institution's completions to in-demand occupations."""

    formula_version: str
    institution_unitid: str
    institution_name: str | None
    total_completions: Decimal
    matched_completions: Decimal
    unmatched_completions: Decimal
    match_rate: Decimal | None
    matched_occupations: tuple[MatchedOccupation, ...]
    caveats: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchedOccupation:
    """A single CIP-to-SOC match with demand context."""

    cip_code: str
    soc_code: str
    annual_completions: Decimal
    annual_openings: Decimal
    surplus: Decimal  # completions - openings (positive = oversupply signal)
    relation: str
    median_wage: Decimal | None


@dataclass(frozen=True, slots=True)
class UniversityPipelineResult:
    """Per-institution pipeline capacity vs. regional occupational demand."""

    formula_version: str
    institution_unitid: str
    institution_name: str | None
    total_annual_completions: Decimal
    total_annual_openings_matched: Decimal
    pipeline_surplus: Decimal  # positive = more completions than openings
    pipeline_deficit: Decimal  # positive = more openings than completions
    net_balance: Decimal
    classification: str
    focus_areas: tuple[str, ...]
    caveats: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetentionRiskInput:
    """Inputs for estimating graduate retention risk."""

    annual_graduates: Decimal
    michigan_resident_share: Decimal  # fraction of graduates who are MI residents
    in_state_job_match_rate: Decimal  # fraction of MI-resident grads with in-state job
    out_migration_rate: Decimal  # fraction of MI-resident grads who leave MI


@dataclass(frozen=True, slots=True)
class RetentionRiskResult:
    """Estimated graduate retention for a candidate institution."""

    formula_version: str
    institution_unitid: str
    institution_name: str | None
    annual_graduates: Decimal
    estimated_michigan_retained: Decimal
    estimated_leaving_michigan: Decimal
    retention_rate: Decimal
    risk_classification: str
    caveats: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BusinessAttractionInput:
    """Inputs for evaluating out-of-state business attraction potential."""

    target_industry_naics: str
    target_occupations: tuple[OccupationDemandInput, ...]
    current_establishments: Decimal
    projected_establishments_5yr: Decimal
    current_employment: Decimal
    projected_employment_5yr: Decimal
    median_wage_target: Decimal | None = None
    median_wage_michigan: Decimal | None = None


@dataclass(frozen=True, slots=True)
class BusinessAttractionResult:
    """Signals for out-of-state business attraction in a target industry."""

    formula_version: str
    target_industry_naics: str
    establishment_growth: Decimal
    employment_growth: Decimal
    employment_growth_rate: Decimal | None
    wage_competitiveness: str
    workforce_depth: str
    attractiveness_score: Decimal  # 0..1 composite signal
    caveats: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UniversityWorkforceSummary:
    """Aggregate summary across all candidate institutions."""

    formula_version: str
    total_partner_institutions: int
    total_annual_completions: Decimal
    total_annual_openings_matched: Decimal
    net_pipeline_balance: Decimal
    aggregate_retention_rate: Decimal | None
    top_deficit_occupations: tuple[str, ...]
    top_surplus_occupations: tuple[str, ...]
    caveats: tuple[str, ...]


# ---------------------------------------------------------------------------
# Core analytics functions
# ---------------------------------------------------------------------------


def degree_relevance(
    *,
    institution: PartnerInstitution,
    completions: list[DegreeRelevanceInput],
    demand: list[OccupationDemandInput],
    crosswalk: list[CrosswalkEdge],
) -> DegreeRelevanceResult:
    """Match an institution's CIP completions to in-demand SOC occupations.

    Uses the official CIP-to-SOC crosswalk edges. Completions for CIP codes
    with no crosswalk edge to any in-demand occupation are reported as
    unmatched. The match rate is completions that map to at least one
    occupation with positive annual openings, divided by total completions.
    """
    if not completions:
        raise ValueError("at least one completion record is required")

    # Index demand by SOC code
    demand_by_soc: dict[str, OccupationDemandInput] = {}
    for d in demand:
        demand_by_soc[d.soc_code] = d

    # Build CIP -> [SOC] mapping from crosswalk, filtered to in-demand SOCs
    cip_to_socs: dict[str, list[str]] = {}
    for edge in crosswalk:
        if edge.cip_code not in cip_to_socs:
            cip_to_socs[edge.cip_code] = []
        if edge.soc_code in demand_by_soc:
            cip_to_socs[edge.cip_code].append(edge.soc_code)

    total_completions = ZERO
    matched_completions = ZERO
    matched_occupations: list[MatchedOccupation] = []

    for comp in completions:
        total_completions += comp.annual_completions
        socs = cip_to_socs.get(comp.cip_code, [])
        if socs:
            matched_completions += comp.annual_completions
            for soc in socs:
                d = demand_by_soc[soc]
                surplus = comp.annual_completions - d.annual_openings
                matched_occupations.append(
                    MatchedOccupation(
                        cip_code=comp.cip_code,
                        soc_code=soc,
                        annual_completions=comp.annual_completions,
                        annual_openings=d.annual_openings,
                        surplus=surplus,
                        relation="related",
                        median_wage=d.median_wage,
                    )
                )

    match_rate = (matched_completions / total_completions) if total_completions > ZERO else None

    return DegreeRelevanceResult(
        formula_version="degree_relevance/v1",
        institution_unitid=institution.unitid,
        institution_name=institution.name,
        total_completions=total_completions,
        matched_completions=matched_completions,
        unmatched_completions=total_completions - matched_completions,
        match_rate=match_rate,
        matched_occupations=tuple(matched_occupations),
        caveats=(
            "CIP-to-SOC crosswalk edges are documented relationships, not probabilities.",
            "A match does not imply the graduate will enter the linked occupation.",
            "Unmatched completions may still serve in-demand occupations via adjacent pathways.",
            "Annual openings are model-based projections and include replacement demand.",
        ),
    )


def university_pipeline_balance(
    *,
    institution: PartnerInstitution,
    completions: list[DegreeRelevanceInput],
    demand: list[OccupationDemandInput],
    crosswalk: list[CrosswalkEdge],
) -> UniversityPipelineResult:
    """Compute net pipeline surplus/deficit for one institution.

    Surplus = total completions mapping to in-demand SOCs - total annual
    openings for those SOCs. Positive net_balance means the institution
    produces more graduates than projected openings absorb (potential
    oversupply or out-migration pressure). Negative means a gap.
    """
    relevance = degree_relevance(
        institution=institution,
        completions=completions,
        demand=demand,
        crosswalk=crosswalk,
    )

    total_completions = relevance.total_completions
    total_openings = ZERO
    seen_socs: set[str] = set()
    for mo in relevance.matched_occupations:
        if mo.soc_code not in seen_socs:
            seen_socs.add(mo.soc_code)
            total_openings += mo.annual_openings

    net = total_completions - total_openings
    if net > ZERO:
        classification = "pipeline_surplus"
        surplus = net
        deficit = ZERO
    elif net < ZERO:
        classification = "pipeline_deficit"
        surplus = ZERO
        deficit = abs(net)
    else:
        classification = "pipeline_balanced"
        surplus = ZERO
        deficit = ZERO

    return UniversityPipelineResult(
        formula_version="university_pipeline_balance/v1",
        institution_unitid=institution.unitid,
        institution_name=institution.name,
        total_annual_completions=total_completions,
        total_annual_openings_matched=total_openings,
        pipeline_surplus=surplus,
        pipeline_deficit=deficit,
        net_balance=net,
        classification=classification,
        focus_areas=institution.focus_areas,
        caveats=(
            "Pipeline balance is a narrow supply/demand comparison, not a labor market forecast.",
            "Completions do not imply Michigan labor-force entry.",
            "Openings include replacement demand; new-growth openings are a subset.",
            "Crosswalk edges are RELATED, not EXACT; some completions may map to multiple SOCs.",
        ),
    )


def retention_risk(
    *,
    institution: PartnerInstitution,
    inputs: RetentionRiskInput,
) -> RetentionRiskResult:
    """Estimate graduate retention risk using explicit caller-supplied rates.

    The model computes:
      retained = graduates * michigan_resident_share * in_state_job_match_rate
      leaving  = graduates - retained

    All rates are caller-supplied and must be in [0, 1]. No causal
    parameters are inferred from the data.
    """
    _validate_rate("michigan_resident_share", inputs.michigan_resident_share)
    _validate_rate("in_state_job_match_rate", inputs.in_state_job_match_rate)
    _validate_rate("out_migration_rate", inputs.out_migration_rate)
    if inputs.annual_graduates < ZERO:
        raise ValueError("annual_graduates must be >= 0")

    # Retained = residents who find in-state work + residents who stay without a job
    # Leaving = non-residents who leave + residents who leave
    # Simplified: retained = grads * (resident_share * (1 - out_migration_rate))
    #            leaving = grads - retained
    retained = inputs.annual_graduates * inputs.michigan_resident_share * (ONE - inputs.out_migration_rate)
    leaving = inputs.annual_graduates - retained
    retention_rate = (retained / inputs.annual_graduates) if inputs.annual_graduates > ZERO else ZERO

    if retention_rate >= Decimal("0.70"):
        risk_classification = "low_risk"
    elif retention_rate >= Decimal("0.50"):
        risk_classification = "moderate_risk"
    elif retention_rate >= Decimal("0.30"):
        risk_classification = "elevated_risk"
    else:
        risk_classification = "high_risk"

    return RetentionRiskResult(
        formula_version="retention_risk/v1",
        institution_unitid=institution.unitid,
        institution_name=institution.name,
        annual_graduates=inputs.annual_graduates,
        estimated_michigan_retained=retained,
        estimated_leaving_michigan=leaving,
        retention_rate=retention_rate,
        risk_classification=risk_classification,
        caveats=(
            "Retention estimate is conditional on caller-supplied rates; not a causal measurement.",
            "michigan_resident_share and out_migration_rate should be backed by IPEDS or LEHD evidence.",
            "in_state_job_match_rate is not used in the simplified formula but is retained for context.",
            "Does not account for seasonal or industry-specific migration patterns.",
        ),
    )


def business_attraction_signal(
    *,
    inputs: BusinessAttractionInput,
) -> BusinessAttractionResult:
    """Evaluate out-of-state business attraction potential for a target industry.

    Computes a composite 0..1 attractiveness score from:
      - establishment growth signal (projected vs. current)
      - employment growth signal
      - wage competitiveness (MI median vs. target)
      - workforce depth (matched openings vs. available supply proxy)

    All inputs are caller-supplied. No causal inference is performed.
    """
    if inputs.current_establishments < ZERO or inputs.projected_establishments_5yr < ZERO:
        raise ValueError("establishment counts must be >= 0")
    if inputs.current_employment < ZERO or inputs.projected_employment_5yr < ZERO:
        raise ValueError("employment counts must be >= 0")

    # Establishment growth
    est_growth = inputs.projected_establishments_5yr - inputs.current_establishments
    emp_growth = inputs.projected_employment_5yr - inputs.current_employment
    emp_growth_rate = (emp_growth / inputs.current_employment) if inputs.current_employment > ZERO else None

    # Wage competitiveness
    if inputs.median_wage_target is not None and inputs.median_wage_michigan is not None:
        if inputs.median_wage_target > 0:
            wage_ratio = inputs.median_wage_michigan / inputs.median_wage_target
            if wage_ratio >= Decimal("0.90"):
                wage_competitiveness = "competitive"
            elif wage_ratio >= Decimal("0.75"):
                wage_competitiveness = "moderately_competitive"
            else:
                wage_competitiveness = "below_target"
        else:
            wage_competitiveness = "unknown"
    else:
        wage_competitiveness = "insufficient_data"

    # Workforce depth: sum of openings across target occupations
    total_openings = sum((d.annual_openings for d in inputs.target_occupations), ZERO)
    if total_openings > Decimal("5000"):
        workforce_depth = "deep"
    elif total_openings > Decimal("1000"):
        workforce_depth = "moderate"
    elif total_openings > ZERO:
        workforce_depth = "shallow"
    else:
        workforce_depth = "none"

    # Composite score (0..1): simple weighted average of available signals
    # Weights: growth 0.3, wage 0.25, workforce depth 0.25, establishment growth 0.20
    score_components: list[Decimal] = []
    weights: list[Decimal] = []

    # Growth component (capped at 0..1)
    if inputs.current_employment > ZERO:
        growth_signal = min(ONE, emp_growth / (inputs.current_employment * Decimal("2")))
        growth_signal = max(ZERO, growth_signal)
        score_components.append(growth_signal)
        weights.append(Decimal("0.30"))

    # Wage component
    if wage_competitiveness == "competitive":
        score_components.append(ONE)
        weights.append(Decimal("0.25"))
    elif wage_competitiveness == "moderately_competitive":
        score_components.append(Decimal("0.60"))
        weights.append(Decimal("0.25"))
    elif wage_competitiveness == "below_target":
        score_components.append(Decimal("0.30"))
        weights.append(Decimal("0.25"))

    # Workforce depth component
    if workforce_depth == "deep":
        score_components.append(ONE)
        weights.append(Decimal("0.25"))
    elif workforce_depth == "moderate":
        score_components.append(Decimal("0.50"))
        weights.append(Decimal("0.25"))
    elif workforce_depth == "shallow":
        score_components.append(Decimal("0.25"))
        weights.append(Decimal("0.25"))

    # Establishment growth component
    if inputs.current_establishments > ZERO:
        est_signal = min(ONE, est_growth / (inputs.current_establishments * Decimal("2")))
        est_signal = max(ZERO, est_signal)
        score_components.append(est_signal)
        weights.append(Decimal("0.20"))

    total_weight = sum(weights, ZERO)
    if total_weight > ZERO and score_components:
        weighted_sum = sum((s * w for s, w in zip(score_components, weights, strict=True)), ZERO)
        attractiveness = weighted_sum / total_weight
    else:
        attractiveness = ZERO

    return BusinessAttractionResult(
        formula_version="business_attraction_signal/v1",
        target_industry_naics=inputs.target_industry_naics,
        establishment_growth=est_growth,
        employment_growth=emp_growth,
        employment_growth_rate=emp_growth_rate,
        wage_competitiveness=wage_competitiveness,
        workforce_depth=workforce_depth,
        attractiveness_score=attractiveness,
        caveats=(
            "Attractiveness score is a deterministic composite of caller-supplied inputs; not a causal estimate.",
            "Does not account for regulatory environment, quality of life, tax incentives, or non-economic factors.",
            "Wage competitiveness uses median wages only; distributional effects are not captured.",
            "Workforce depth is a proxy based on projected openings, not actual available labor supply.",
            "Out-of-state business decisions involve factors beyond this model's scope.",
        ),
    )


def university_workforce_summary(
    *,
    institutions: tuple[PartnerInstitution, ...] = PARTNER_INSTITUTIONS,
    pipeline_results: list[UniversityPipelineResult],
    retention_results: list[RetentionRiskResult] | None = None,
) -> UniversityWorkforceSummary:
    """Aggregate summary across all candidate institutions."""
    if not pipeline_results:
        raise ValueError("at least one pipeline result is required")

    total_completions = sum((r.total_annual_completions for r in pipeline_results), ZERO)
    total_openings = sum((r.total_annual_openings_matched for r in pipeline_results), ZERO)
    net_balance = total_completions - total_openings

    # Aggregate retention
    if retention_results:
        total_grads = sum((r.annual_graduates for r in retention_results), ZERO)
        total_retained = sum((r.estimated_michigan_retained for r in retention_results), ZERO)
        aggregate_retention = (total_retained / total_grads) if total_grads > ZERO else None
    else:
        aggregate_retention = None

    # Top deficit/surplus occupations
    deficit_occs: list[tuple[Decimal, str]] = []
    surplus_occs: list[tuple[Decimal, str]] = []
    for r in pipeline_results:
        if r.pipeline_deficit > ZERO:
            deficit_occs.append((r.pipeline_deficit, r.institution_unitid))
        if r.pipeline_surplus > ZERO:
            surplus_occs.append((r.pipeline_surplus, r.institution_unitid))

    top_deficits = tuple(u for _, u in sorted(deficit_occs, reverse=True)[:5])
    top_surpluses = tuple(u for _, u in sorted(surplus_occs, reverse=True)[:5])

    return UniversityWorkforceSummary(
        formula_version="university_workforce_summary/v1",
        total_partner_institutions=len(institutions),
        total_annual_completions=total_completions,
        total_annual_openings_matched=total_openings,
        net_pipeline_balance=net_balance,
        aggregate_retention_rate=aggregate_retention,
        top_deficit_occupations=top_deficits,
        top_surplus_occupations=top_surpluses,
        caveats=(
            "Summary aggregates candidate institutions only; does not represent all Michigan postsecondary supply.",
            "Pipeline balance is a narrow comparison, not a labor market forecast.",
            "Retention data is optional; absence is reported, not imputed.",
            "Top deficit/surplus lists are by institution, not by occupation (occupation-level detail in individual results).",
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_rate(name: str, value: Decimal) -> None:
    if value < ZERO or value > ONE:
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def crosswalk_edges_from_mappings(
    mappings: list[dict[str, Any]],
) -> list[CrosswalkEdge]:
    """Convert raw mapping dicts (from MCP or repository) to CrosswalkEdge objects.

    Expected dict keys: from_code, from_version, to_code, to_version, relation, weight.
    """
    edges: list[CrosswalkEdge] = []
    for m in mappings:
        edges.append(
            CrosswalkEdge(
                cip_code=m["from_code"],
                cip_version=m.get("from_version", "2020"),
                soc_code=m["to_code"],
                soc_version=m.get("to_version", "2018"),
                relation=m.get("relation", "related"),
                weight=m.get("weight"),
            )
        )
    return edges


def degree_relevance_inputs_from_observations(
    observations: list[dict[str, Any]],
    institution_unitid: str,
) -> list[DegreeRelevanceInput]:
    """Convert raw observation dicts to DegreeRelevanceInput objects.

    Expects observations with metric='ipeds.completions.awards',
    geography_code=institution_unitid, taxonomy_system='CIP'.
    """
    inputs: list[DegreeRelevanceInput] = []
    for obs in observations:
        if obs.get("metric") != "ipeds.completions.awards":
            continue
        if obs.get("geography_code") != institution_unitid:
            continue
        if obs.get("taxonomy_system") != "CIP":
            continue
        numeric = obs.get("numeric_value")
        if numeric is None:
            continue
        inputs.append(
            DegreeRelevanceInput(
                institution_unitid=institution_unitid,
                cip_code=obs.get("taxonomy_code", ""),
                cip_version=obs.get("taxonomy_version", "2020"),
                annual_completions=Decimal(str(numeric)),
                period_basis=obs.get("period_basis", "academic_year"),
                period_start=obs.get("period_start"),
                period_end=obs.get("period_end"),
            )
        )
    return inputs


def occupation_demand_inputs_from_observations(
    observations: list[dict[str, Any]],
    geography_code: str,
) -> list[OccupationDemandInput]:
    """Convert raw observation dicts to OccupationDemandInput objects.

    Expects observations with metric containing 'openings' or 'projections',
    geography_code matching the target, taxonomy_system='SOC'.
    """
    inputs: list[OccupationDemandInput] = []
    for obs in observations:
        metric = obs.get("metric", "")
        if "opening" not in metric.lower() and "projection" not in metric.lower():
            continue
        if obs.get("geography_code") != geography_code:
            continue
        if obs.get("taxonomy_system") != "SOC":
            continue
        numeric = obs.get("numeric_value")
        if numeric is None:
            continue
        inputs.append(
            OccupationDemandInput(
                soc_code=obs.get("taxonomy_code", ""),
                soc_version=obs.get("taxonomy_version", "2018"),
                annual_openings=Decimal(str(numeric)),
                geography_code=geography_code,
                period_basis=obs.get("period_basis", "annual"),
            )
        )
    return inputs
