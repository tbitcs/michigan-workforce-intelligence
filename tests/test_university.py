from __future__ import annotations

from decimal import Decimal

import pytest

from mijobs.analytics.university import (
    BusinessAttractionInput,
    CrosswalkEdge,
    DegreeRelevanceInput,
    OccupationDemandInput,
    RetentionRiskInput,
    RetentionRiskResult,
    UniversityPipelineResult,
    business_attraction_signal,
    crosswalk_edges_from_mappings,
    degree_relevance,
    degree_relevance_inputs_from_observations,
    occupation_demand_inputs_from_observations,
    retention_risk,
    university_pipeline_balance,
    university_workforce_summary,
)
from mijobs.sources.institutions import (
    PARTNER_INSTITUTIONS,
    PARTNER_UNITIDS,
    get_partner_institution,
    partner_institutions_by_focus,
)

# ---------------------------------------------------------------------------
# Partner institution registry tests
# ---------------------------------------------------------------------------


class TestPartnerInstitutions:
    def test_all_partner_institutions_have_valid_unitids(self):
        for inst in PARTNER_INSTITUTIONS:
            assert inst.unitid.isdigit()
            assert len(inst.unitid) == 6

    def test_partner_unitids_are_unique(self):
        assert len(PARTNER_UNITIDS) == len(PARTNER_INSTITUTIONS)

    def test_get_partner_institution_found(self):
        inst = get_partner_institution("170675")
        assert inst is not None
        assert inst.name == "Lawrence Technological University"

    def test_get_partner_institution_not_found(self):
        assert get_partner_institution("999999") is None

    def test_partner_institutions_by_focus(self):
        eng = partner_institutions_by_focus("engineering")
        assert len(eng) >= 2
        names = {i.name for i in eng}
        assert "Lawrence Technological University" in names
        assert "Oakland University" in names

    def test_partner_institutions_by_focus_no_match(self):
        assert partner_institutions_by_focus("marine_biology") == ()

    def test_lawrence_tech_exists(self):
        inst = get_partner_institution("170675")
        assert inst is not None
        assert inst.city == "Southfield"
        assert inst.state == "MI"

    def test_rochester_college_exists(self):
        inst = get_partner_institution("170967")
        assert inst is not None
        assert inst.name == "Rochester Christian University"
        assert inst.city == "Rochester Hills"

    def test_oakland_university_exists(self):
        inst = get_partner_institution("171571")
        assert inst is not None
        assert inst.name == "Oakland University"
        assert inst.control == "Public"

    def test_kettering_exists(self):
        inst = get_partner_institution("169983")
        assert inst is not None
        assert inst.name == "Kettering University"
        assert inst.city == "Flint"


# ---------------------------------------------------------------------------
# Degree relevance tests
# ---------------------------------------------------------------------------


class TestDegreeRelevance:
    def setup_method(self):
        self.institution = get_partner_institution("170675")
        assert self.institution is not None
        self.completions = [
            DegreeRelevanceInput(
                institution_unitid="170675",
                cip_code="15.1001",
                cip_version="2020",
                annual_completions=Decimal("200"),
            ),
            DegreeRelevanceInput(
                institution_unitid="170675",
                cip_code="24.0101",
                cip_version="2020",
                annual_completions=Decimal("150"),
            ),
            DegreeRelevanceInput(
                institution_unitid="170675",
                cip_code="99.9999",
                cip_version="2020",
                annual_completions=Decimal("50"),
            ),
        ]
        self.demand = [
            OccupationDemandInput(
                soc_code="15-1252",
                soc_version="2018",
                annual_openings=Decimal("300"),
                geography_code="MI",
                median_wage=Decimal("95000"),
            ),
            OccupationDemandInput(
                soc_code="17-2141",
                soc_version="2018",
                annual_openings=Decimal("100"),
                geography_code="MI",
                median_wage=Decimal("85000"),
            ),
        ]
        self.crosswalk = [
            CrosswalkEdge(
                cip_code="15.1001",
                cip_version="2020",
                soc_code="15-1252",
                soc_version="2018",
                relation="related",
            ),
            CrosswalkEdge(
                cip_code="24.0101",
                cip_version="2020",
                soc_code="17-2141",
                soc_version="2018",
                relation="related",
            ),
        ]

    def test_basic_match(self):
        result = degree_relevance(
            institution=self.institution,
            completions=self.completions,
            demand=self.demand,
            crosswalk=self.crosswalk,
        )
        assert result.total_completions == Decimal("400")
        assert result.matched_completions == Decimal("350")
        assert result.unmatched_completions == Decimal("50")
        assert result.match_rate == Decimal("350") / Decimal("400")

    def test_unmatched_cip_code(self):
        result = degree_relevance(
            institution=self.institution,
            completions=self.completions,
            demand=self.demand,
            crosswalk=self.crosswalk,
        )
        # CIP 99.9999 has no crosswalk edge
        assert result.unmatched_completions == Decimal("50")

    def test_empty_completions_raises(self):
        with pytest.raises(ValueError, match="at least one completion"):
            degree_relevance(
                institution=self.institution,
                completions=[],
                demand=self.demand,
                crosswalk=self.crosswalk,
            )

    def test_institution_name_in_result(self):
        result = degree_relevance(
            institution=self.institution,
            completions=self.completions,
            demand=self.demand,
            crosswalk=self.crosswalk,
        )
        assert result.institution_name == "Lawrence Technological University"
        assert result.institution_unitid == "170675"

    def test_formula_version(self):
        result = degree_relevance(
            institution=self.institution,
            completions=self.completions,
            demand=self.demand,
            crosswalk=self.crosswalk,
        )
        assert result.formula_version == "degree_relevance/v1"

    def test_caveats_present(self):
        result = degree_relevance(
            institution=self.institution,
            completions=self.completions,
            demand=self.demand,
            crosswalk=self.crosswalk,
        )
        assert len(result.caveats) >= 3

    def test_matched_occupations_populated(self):
        result = degree_relevance(
            institution=self.institution,
            completions=self.completions,
            demand=self.demand,
            crosswalk=self.crosswalk,
        )
        assert len(result.matched_occupations) == 2
        soc_codes = {mo.soc_code for mo in result.matched_occupations}
        assert "15-1252" in soc_codes
        assert "17-2141" in soc_codes


# ---------------------------------------------------------------------------
# Pipeline balance tests
# ---------------------------------------------------------------------------


class TestUniversityPipelineBalance:
    def setup_method(self):
        self.institution = get_partner_institution("171571")
        assert self.institution is not None
        self.completions = [
            DegreeRelevanceInput(
                institution_unitid="171571",
                cip_code="15.1001",
                cip_version="2020",
                annual_completions=Decimal("500"),
            ),
        ]
        self.demand = [
            OccupationDemandInput(
                soc_code="15-1252",
                soc_version="2018",
                annual_openings=Decimal("300"),
                geography_code="MI",
            ),
        ]
        self.crosswalk = [
            CrosswalkEdge(
                cip_code="15.1001",
                cip_version="2020",
                soc_code="15-1252",
                soc_version="2018",
            ),
        ]

    def test_surplus(self):
        result = university_pipeline_balance(
            institution=self.institution,
            completions=self.completions,
            demand=self.demand,
            crosswalk=self.crosswalk,
        )
        assert result.classification == "pipeline_surplus"
        assert result.pipeline_surplus == Decimal("200")
        assert result.pipeline_deficit == Decimal("0")
        assert result.net_balance == Decimal("200")

    def test_deficit(self):
        demand = [
            OccupationDemandInput(
                soc_code="15-1252",
                soc_version="2018",
                annual_openings=Decimal("700"),
                geography_code="MI",
            ),
        ]
        result = university_pipeline_balance(
            institution=self.institution,
            completions=self.completions,
            demand=demand,
            crosswalk=self.crosswalk,
        )
        assert result.classification == "pipeline_deficit"
        assert result.pipeline_deficit == Decimal("200")
        assert result.pipeline_surplus == Decimal("0")
        assert result.net_balance == Decimal("-200")

    def test_balanced(self):
        demand = [
            OccupationDemandInput(
                soc_code="15-1252",
                soc_version="2018",
                annual_openings=Decimal("500"),
                geography_code="MI",
            ),
        ]
        result = university_pipeline_balance(
            institution=self.institution,
            completions=self.completions,
            demand=demand,
            crosswalk=self.crosswalk,
        )
        assert result.classification == "pipeline_balanced"
        assert result.net_balance == Decimal("0")

    def test_focus_areas_preserved(self):
        result = university_pipeline_balance(
            institution=self.institution,
            completions=self.completions,
            demand=self.demand,
            crosswalk=self.crosswalk,
        )
        assert "engineering" in result.focus_areas


# ---------------------------------------------------------------------------
# Retention risk tests
# ---------------------------------------------------------------------------


class TestRetentionRisk:
    def setup_method(self):
        self.institution = get_partner_institution("170675")
        assert self.institution is not None

    def test_low_risk(self):
        inputs = RetentionRiskInput(
            annual_graduates=Decimal("1000"),
            michigan_resident_share=Decimal("0.80"),
            in_state_job_match_rate=Decimal("0.70"),
            out_migration_rate=Decimal("0.10"),
        )
        result = retention_risk(institution=self.institution, inputs=inputs)
        # retained = 1000 * 0.80 * (1 - 0.10) = 720
        assert result.estimated_michigan_retained == Decimal("720")
        assert result.estimated_leaving_michigan == Decimal("280")
        assert result.retention_rate == Decimal("0.72")
        assert result.risk_classification == "low_risk"

    def test_high_risk(self):
        inputs = RetentionRiskInput(
            annual_graduates=Decimal("1000"),
            michigan_resident_share=Decimal("0.40"),
            in_state_job_match_rate=Decimal("0.50"),
            out_migration_rate=Decimal("0.50"),
        )
        result = retention_risk(institution=self.institution, inputs=inputs)
        # retained = 1000 * 0.40 * (1 - 0.50) = 200
        assert result.estimated_michigan_retained == Decimal("200")
        assert result.retention_rate == Decimal("0.20")
        assert result.risk_classification == "high_risk"

    def test_moderate_risk(self):
        inputs = RetentionRiskInput(
            annual_graduates=Decimal("1000"),
            michigan_resident_share=Decimal("0.60"),
            in_state_job_match_rate=Decimal("0.60"),
            out_migration_rate=Decimal("0.30"),
        )
        result = retention_risk(institution=self.institution, inputs=inputs)
        # retained = 1000 * 0.60 * 0.70 = 420
        assert result.estimated_michigan_retained == Decimal("420")
        assert result.retention_rate == Decimal("0.42")
        assert result.risk_classification == "elevated_risk"

    def test_invalid_rate_raises(self):
        inputs = RetentionRiskInput(
            annual_graduates=Decimal("1000"),
            michigan_resident_share=Decimal("1.5"),  # > 1
            in_state_job_match_rate=Decimal("0.5"),
            out_migration_rate=Decimal("0.2"),
        )
        with pytest.raises(ValueError, match="michigan_resident_share"):
            retention_risk(institution=self.institution, inputs=inputs)

    def test_negative_graduates_raises(self):
        inputs = RetentionRiskInput(
            annual_graduates=Decimal("-100"),
            michigan_resident_share=Decimal("0.5"),
            in_state_job_match_rate=Decimal("0.5"),
            out_migration_rate=Decimal("0.2"),
        )
        with pytest.raises(ValueError, match="annual_graduates"):
            retention_risk(institution=self.institution, inputs=inputs)

    def test_zero_graduates(self):
        inputs = RetentionRiskInput(
            annual_graduates=Decimal("0"),
            michigan_resident_share=Decimal("0.5"),
            in_state_job_match_rate=Decimal("0.5"),
            out_migration_rate=Decimal("0.2"),
        )
        result = retention_risk(institution=self.institution, inputs=inputs)
        assert result.estimated_michigan_retained == Decimal("0")
        assert result.retention_rate == Decimal("0")


# ---------------------------------------------------------------------------
# Business attraction tests
# ---------------------------------------------------------------------------


class TestBusinessAttraction:
    def test_attractive_industry(self):
        inputs = BusinessAttractionInput(
            target_industry_naics="336411",
            target_occupations=(
                OccupationDemandInput(
                    soc_code="17-2141",
                    soc_version="2018",
                    annual_openings=Decimal("6000"),
                    geography_code="MI",
                ),
            ),
            current_establishments=Decimal("100"),
            projected_establishments_5yr=Decimal("150"),
            current_employment=Decimal("5000"),
            projected_employment_5yr=Decimal("8000"),
            median_wage_target=Decimal("90000"),
            median_wage_michigan=Decimal("85000"),
        )
        result = business_attraction_signal(inputs=inputs)
        assert result.establishment_growth == Decimal("50")
        assert result.employment_growth == Decimal("3000")
        assert result.employment_growth_rate is not None
        assert result.wage_competitiveness == "competitive"
        assert result.workforce_depth == "deep"
        assert result.attractiveness_score > Decimal("0")
        assert result.attractiveness_score <= Decimal("1")

    def test_unattractive_industry(self):
        inputs = BusinessAttractionInput(
            target_industry_naics="445292",
            target_occupations=(
                OccupationDemandInput(
                    soc_code="41-2031",
                    soc_version="2018",
                    annual_openings=Decimal("500"),
                    geography_code="MI",
                ),
            ),
            current_establishments=Decimal("500"),
            projected_establishments_5yr=Decimal("400"),
            current_employment=Decimal("10000"),
            projected_employment_5yr=Decimal("8000"),
            median_wage_target=Decimal("100000"),
            median_wage_michigan=Decimal("60000"),
        )
        result = business_attraction_signal(inputs=inputs)
        assert result.establishment_growth == Decimal("-100")
        assert result.employment_growth == Decimal("-2000")
        assert result.wage_competitiveness == "below_target"
        assert result.workforce_depth == "shallow"

    def test_no_occupations(self):
        inputs = BusinessAttractionInput(
            target_industry_naics="519130",
            target_occupations=(),
            current_establishments=Decimal("10"),
            projected_establishments_5yr=Decimal("12"),
            current_employment=Decimal("50"),
            projected_employment_5yr=Decimal("60"),
        )
        result = business_attraction_signal(inputs=inputs)
        assert result.workforce_depth == "none"
        assert result.wage_competitiveness == "insufficient_data"

    def test_negative_establishments_raises(self):
        inputs = BusinessAttractionInput(
            target_industry_naics="336411",
            target_occupations=(),
            current_establishments=Decimal("-1"),
            projected_establishments_5yr=Decimal("10"),
            current_employment=Decimal("100"),
            projected_employment_5yr=Decimal("150"),
        )
        with pytest.raises(ValueError, match="establishment"):
            business_attraction_signal(inputs=inputs)

    def test_zero_current_employment_no_division_error(self):
        inputs = BusinessAttractionInput(
            target_industry_naics="336411",
            target_occupations=(),
            current_establishments=Decimal("10"),
            projected_establishments_5yr=Decimal("15"),
            current_employment=Decimal("0"),
            projected_employment_5yr=Decimal("100"),
        )
        result = business_attraction_signal(inputs=inputs)
        assert result.employment_growth_rate is None


# ---------------------------------------------------------------------------
# University workforce summary tests
# ---------------------------------------------------------------------------


class TestUniversityWorkforceSummary:
    def test_summary_with_pipeline_results(self):
        pipeline_results = [
            UniversityPipelineResult(
                formula_version="university_pipeline_balance/v1",
                institution_unitid="170675",
                institution_name="Lawrence Technological University",
                total_annual_completions=Decimal("500"),
                total_annual_openings_matched=Decimal("300"),
                pipeline_surplus=Decimal("200"),
                pipeline_deficit=Decimal("0"),
                net_balance=Decimal("200"),
                classification="pipeline_surplus",
                focus_areas=("engineering",),
                caveats=(),
            ),
            UniversityPipelineResult(
                formula_version="university_pipeline_balance/v1",
                institution_unitid="171571",
                institution_name="Oakland University",
                total_annual_completions=Decimal("800"),
                total_annual_openings_matched=Decimal("1200"),
                pipeline_surplus=Decimal("0"),
                pipeline_deficit=Decimal("400"),
                net_balance=Decimal("-400"),
                classification="pipeline_deficit",
                focus_areas=("engineering", "computer_science"),
                caveats=(),
            ),
        ]
        result = university_workforce_summary(
            pipeline_results=pipeline_results,
        )
        assert result.total_annual_completions == Decimal("1300")
        assert result.total_annual_openings_matched == Decimal("1500")
        assert result.net_pipeline_balance == Decimal("-200")
        assert result.total_partner_institutions == 4
        assert "171571" in result.top_deficit_occupations
        assert "170675" in result.top_surplus_occupations

    def test_summary_with_retention(self):
        pipeline_results = [
            UniversityPipelineResult(
                formula_version="university_pipeline_balance/v1",
                institution_unitid="170675",
                institution_name="Lawrence Technological University",
                total_annual_completions=Decimal("500"),
                total_annual_openings_matched=Decimal("300"),
                pipeline_surplus=Decimal("200"),
                pipeline_deficit=Decimal("0"),
                net_balance=Decimal("200"),
                classification="pipeline_surplus",
                focus_areas=(),
                caveats=(),
            ),
        ]
        retention_results = [
            RetentionRiskResult(
                formula_version="retention_risk/v1",
                institution_unitid="170675",
                institution_name="Lawrence Technological University",
                annual_graduates=Decimal("500"),
                estimated_michigan_retained=Decimal("350"),
                estimated_leaving_michigan=Decimal("150"),
                retention_rate=Decimal("0.70"),
                risk_classification="low_risk",
                caveats=(),
            ),
        ]
        result = university_workforce_summary(
            pipeline_results=pipeline_results,
            retention_results=retention_results,
        )
        assert result.aggregate_retention_rate == Decimal("0.70")

    def test_summary_empty_pipeline_raises(self):
        with pytest.raises(ValueError, match="at least one pipeline"):
            university_workforce_summary(pipeline_results=[])


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_crosswalk_edges_from_mappings(self):
        raw = [
            {
                "from_code": "15.1001",
                "from_version": "2020",
                "to_code": "15-1252",
                "to_version": "2018",
                "relation": "related",
                "weight": None,
            },
        ]
        edges = crosswalk_edges_from_mappings(raw)
        assert len(edges) == 1
        assert edges[0].cip_code == "15.1001"
        assert edges[0].soc_code == "15-1252"
        assert edges[0].relation == "related"

    def test_degree_relevance_inputs_from_observations(self):
        obs = [
            {
                "metric": "ipeds.completions.awards",
                "geography_code": "170675",
                "taxonomy_system": "CIP",
                "taxonomy_code": "15.1001",
                "taxonomy_version": "2020",
                "numeric_value": 200.0,
                "period_basis": "academic_year",
                "period_start": "2023-07-01",
                "period_end": "2024-06-30",
            },
            {
                "metric": "ipeds.enrollment.fall",
                "geography_code": "170675",
                "taxonomy_system": "CIP",
                "taxonomy_code": "15.1001",
                "numeric_value": 5000.0,
            },
        ]
        inputs = degree_relevance_inputs_from_observations(obs, "170675")
        assert len(inputs) == 1
        assert inputs[0].cip_code == "15.1001"
        assert inputs[0].annual_completions == Decimal("200.0")

    def test_occupation_demand_inputs_from_observations(self):
        obs = [
            {
                "metric": "mcda.occupation.annual_openings",
                "geography_code": "MI",
                "taxonomy_system": "SOC",
                "taxonomy_code": "15-1252",
                "taxonomy_version": "2018",
                "numeric_value": 300.0,
                "period_basis": "annual",
            },
            {
                "metric": "bls.unemployment_rate",
                "geography_code": "MI",
                "taxonomy_system": "SOC",
                "taxonomy_code": "15-1252",
                "numeric_value": 4.2,
            },
        ]
        inputs = occupation_demand_inputs_from_observations(obs, "MI")
        assert len(inputs) == 1
        assert inputs[0].soc_code == "15-1252"
        assert inputs[0].annual_openings == Decimal("300.0")
