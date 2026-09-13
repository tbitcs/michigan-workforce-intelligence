"""September 2026 insights report generator.

Computes derived metrics from harvested observations, creates versioned claims
with evidence links, and produces a structured report dict suitable for
downstream report writing.

Design principles:
- All derived metrics reference their input observations explicitly.
- Claims are versioned; re-running supersedes prior versions.
- Missing data produces explicit "insufficient_data" status, never imputation.
- The report is a structured dict — prose generation is a separate concern.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from mijobs.domain import ClaimKind, ClaimStatus, EvidenceRelation, EvidenceType
from mijobs.models import Observation
from mijobs.repository import EvidenceRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReportSection:
    """A single section of the insights report."""

    title: str
    metric_name: str
    value: str
    unit: str
    period: str
    status: str  # "computed" | "insufficient_data"
    caveats: tuple[str, ...] = ()
    derived_metric_id: str | None = None
    claim_id: str | None = None


@dataclass(frozen=True, slots=True)
class InsightsReport:
    """Structured output of the insights report generator."""

    generated_at: str
    reporting_period: str
    sections: tuple[ReportSection, ...]
    data_coverage: dict[str, Any]
    ledger_valid: bool
    total_derived_metrics: int
    total_claims: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "mijobs-insights-report/v1",
            "generated_at": self.generated_at,
            "reporting_period": self.reporting_period,
            "sections": [
                {
                    "title": s.title,
                    "metric_name": s.metric_name,
                    "value": s.value,
                    "unit": s.unit,
                    "period": s.period,
                    "status": s.status,
                    "caveats": list(s.caveats),
                    "derived_metric_id": s.derived_metric_id,
                    "claim_id": s.claim_id,
                }
                for s in self.sections
            ],
            "data_coverage": self.data_coverage,
            "ledger_valid": self.ledger_valid,
            "total_derived_metrics": self.total_derived_metrics,
            "total_claims": self.total_claims,
        }


class InsightsReportGenerator:
    """Generates a structured insights report from harvested observations.

    The generator:
    1. Queries relevant observations from the database.
    2. Computes derived metrics (trends, changes, ratios).
    3. Creates versioned claims with evidence links.
    4. Returns a structured report dict.
    """

    def __init__(self, session: Session, *, actor: str = "report-generator"):
        self.session = session
        self.repo = EvidenceRepository(session, actor=actor)

    def generate(self, *, as_of: date | None = None) -> InsightsReport:
        """Generate the full insights report.

        Args:
            as_of: The reference date for the report. Defaults to today.
        """
        if as_of is None:
            as_of = date.today()

        from mijobs.ledger import audit_evidence_coverage, verify_ledger

        if not verify_ledger(self.session).valid or not audit_evidence_coverage(self.session).valid:
            raise RuntimeError("Cannot generate insights from unaudited evidence")

        year = as_of.year
        month = as_of.month
        reporting_period = f"{year}-{month:02d}"

        # Query observations
        bls_obs = [o for o in self._query_bls_observations(year)
                   if o.period_start is not None and o.period_start <= as_of]
        qwi_obs = [o for o in self._query_qwi_observations(year)
                   if o.period_start is not None and o.period_start <= as_of]

        # Compute derived metrics and build sections
        sections: list[ReportSection] = []
        derived_count = 0
        claim_count = 0

        # --- Section 1: National unemployment rate (latest) ---
        section = self._compute_unemployment_rate(bls_obs, year, month)
        if section:
            sections.append(section)
            if section.derived_metric_id:
                derived_count += 1
            if section.claim_id:
                claim_count += 1

        # --- Section 2: Unemployment rate YoY change ---
        section = self._compute_unemployment_rate_yoy(bls_obs, year, month)
        if section:
            sections.append(section)
            if section.derived_metric_id:
                derived_count += 1
            if section.claim_id:
                claim_count += 1

        # --- Section 3: Unemployed persons (latest) ---
        section = self._compute_unemployed_level(bls_obs, year, month)
        if section:
            sections.append(section)
            if section.derived_metric_id:
                derived_count += 1
            if section.claim_id:
                claim_count += 1

        # --- Section 4: Labor force (latest) ---
        section = self._compute_labor_force(bls_obs, year, month)
        if section:
            sections.append(section)
            if section.derived_metric_id:
                derived_count += 1
            if section.claim_id:
                claim_count += 1

        # --- Section 5: QWI Michigan employment (latest quarter) ---
        section = self._compute_qwi_employment(qwi_obs, year)
        if section:
            sections.append(section)
            if section.derived_metric_id:
                derived_count += 1
            if section.claim_id:
                claim_count += 1

        # --- Section 6: QWI employment YoY change ---
        section = self._compute_qwi_employment_yoy(qwi_obs, year)
        if section:
            sections.append(section)
            if section.derived_metric_id:
                derived_count += 1
            if section.claim_id:
                claim_count += 1

        # Data coverage summary
        coverage = self._compute_coverage(bls_obs, qwi_obs, year)

        # Ledger validity check
        from mijobs.ledger import verify_ledger

        ledger_result = verify_ledger(self.session)

        return InsightsReport(
            generated_at=datetime.now(UTC).isoformat(),
            reporting_period=reporting_period,
            sections=tuple(sections),
            data_coverage=coverage,
            ledger_valid=ledger_result.valid,
            total_derived_metrics=derived_count,
            total_claims=claim_count,
        )

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _query_bls_observations(self, year: int) -> list[Observation]:
        """Query BLS CPS observations for the given year and prior year."""
        # We need current year + prior year for YoY calculations
        start = date(year - 1, 1, 1)
        end = date(year, 12, 31)
        newer = aliased(Observation)
        stmt = (
            select(Observation)
            .where(~select(newer.id).where(newer.observation_key == Observation.observation_key,
                                          newer.version > Observation.version).exists())
            .where(Observation.metric.like("bls.cps.%"))
            .where(Observation.geography_code == "US")
            .where(Observation.period_basis == "monthly")
            .where(Observation.period_start >= start)
            .where(Observation.period_start <= end)
            .order_by(Observation.period_start)
        )
        return list(self.session.scalars(stmt))

    def _query_qwi_observations(self, year: int) -> list[Observation]:
        """Query all available QWI observations for Michigan.

        QWI data lags significantly, so we query all available data rather
        than a narrow time window. The compute methods will select the
        latest and same-quarter-prior-year observations as needed.
        """
        newer = aliased(Observation)
        stmt = (
            select(Observation)
            .where(~select(newer.id).where(newer.observation_key == Observation.observation_key,
                                          newer.version > Observation.version).exists())
            .where(Observation.metric == "qwi.Emp")
            .where(Observation.geography_code == "26")
            .order_by(Observation.period_start)
        )
        return list(self.session.scalars(stmt))

    # ------------------------------------------------------------------
    # Derived metric computations
    # ------------------------------------------------------------------

    def _compute_unemployment_rate(
        self, obs: list[Observation], year: int, month: int
    ) -> ReportSection | None:
        """Latest national unemployment rate."""
        # Filter to unemployment rate series
        rate_obs = [o for o in obs if o.metric == "bls.cps.LNS14000000"]
        # Get the most recent observation with a numeric value
        latest = self._latest_numeric(rate_obs, year, month)
        if latest is None or latest.numeric_value is None or latest.period_start is None:
            return self._insufficient_section("National Unemployment Rate", "bls.cps.unemployment_rate")

        value = latest.numeric_value
        period_str = f"{latest.period_start.year}-{latest.period_start.month:02d}"
        input_ref = {"type": "observation", "id": latest.id}

        dm = self.repo.add_derived_metric(
            derivation_key=f"insights:unemp_rate:{period_str}",
            formula_name="latest_observation",
            formula_version="latest_obs/v1",
            metric="bls.cps.unemployment_rate",
            value_text=f"{value:.1f}%",
            unit="percent",
            numeric_value=float(value),
            input_refs=[input_ref],
            scope={"geography": "US", "period": period_str},
            caveats=["Seasonally adjusted. Subject to revision."],
        )

        claim = self.repo.add_claim(
            claim_key=f"insights:unemp_rate:{period_str}",
            text=f"U.S. seasonally-adjusted unemployment rate was {value:.1f}% in {period_str}.",
            kind=ClaimKind.REPORTED,
            status=ClaimStatus.SUPPORTED,
            scope={"geography": "US", "period": period_str},
        )
        self.repo.add_evidence(
            claim_id=claim.id,
            evidence_type=EvidenceType.OBSERVATION,
            evidence_id=latest.id,
            relation=EvidenceRelation.SUPPORTS,
            rationale="Direct observation from BLS CPS series LNS14000000",
        )

        return ReportSection(
            title="U.S. Unemployment Rate (Latest)",
            metric_name="bls.cps.unemployment_rate",
            value=f"{value:.1f}%",
            unit="percent",
            period=period_str,
            status="computed",
            caveats=("Seasonally adjusted. Subject to revision.",),
            derived_metric_id=dm.id,
            claim_id=claim.id,
        )

    def _compute_unemployment_rate_yoy(
        self, obs: list[Observation], year: int, month: int
    ) -> ReportSection | None:
        """Year-over-year change in unemployment rate."""
        rate_obs = [o for o in obs if o.metric == "bls.cps.LNS14000000"]
        current = self._latest_numeric(rate_obs, year, month)
        if current is None or current.numeric_value is None:
            return self._insufficient_section("Unemployment Rate YoY Change", "bls.cps.unemp_rate_yoy")

        # Find same month prior year
        assert current.period_start is not None
        year, month = current.period_start.year, current.period_start.month
        prior_year = year - 1
        prior_obs = [
            o
            for o in rate_obs
            if o.numeric_value is not None
            and o.period_start is not None
            and o.period_start.year == prior_year
            and o.period_start.month == month
        ]
        if not prior_obs:
            return self._insufficient_section("Unemployment Rate YoY Change", "bls.cps.unemp_rate_yoy")

        prior = prior_obs[0]
        if prior.numeric_value is None:
            return self._insufficient_section("Unemployment Rate YoY Change", "bls.cps.unemp_rate_yoy")
        change = current.numeric_value - prior.numeric_value
        period_str = f"{year}-{month:02d}"
        input_refs = [
            {"type": "observation", "id": current.id},
            {"type": "observation", "id": prior.id},
        ]

        dm = self.repo.add_derived_metric(
            derivation_key=f"insights:unemp_rate_yoy:{period_str}",
            formula_name="yoy_change",
            formula_version="yoy/v1",
            metric="bls.cps.unemp_rate_yoy_change",
            value_text=f"{change:+.1f} pp",
            unit="percentage_points",
            numeric_value=float(change),
            input_refs=input_refs,
            scope={"geography": "US", "period": period_str},
            caveats=["YoY comparison; both values seasonally adjusted."],
        )

        direction = "increased" if change > 0 else "decreased"
        claim = self.repo.add_claim(
            claim_key=f"insights:unemp_rate_yoy:{period_str}",
            text=(
                f"U.S. unemployment rate {direction} by {abs(change):.1f} percentage points "
                f"year-over-year ({prior.numeric_value:.1f}% in {prior_year}-{month:02d} → "
                f"{current.numeric_value:.1f}% in {period_str})."
            ),
            kind=ClaimKind.DERIVED,
            status=ClaimStatus.SUPPORTED,
            scope={"geography": "US", "period": period_str},
        )
        self.repo.add_evidence(
            claim_id=claim.id,
            evidence_type=EvidenceType.DERIVED_METRIC,
            evidence_id=dm.id,
            relation=EvidenceRelation.DERIVES_FROM,
            rationale="Computed from two BLS CPS observations",
        )

        return ReportSection(
            title="Unemployment Rate YoY Change",
            metric_name="bls.cps.unemp_rate_yoy_change",
            value=f"{change:+.1f} pp",
            unit="percentage_points",
            period=period_str,
            status="computed",
            caveats=("YoY comparison; both values seasonally adjusted.",),
            derived_metric_id=dm.id,
            claim_id=claim.id,
        )

    def _compute_unemployed_level(
        self, obs: list[Observation], year: int, month: int
    ) -> ReportSection | None:
        """Latest unemployed persons level."""
        level_obs = [o for o in obs if o.metric == "bls.cps.LNS13000000"]
        latest = self._latest_numeric(level_obs, year, month)
        if latest is None or latest.numeric_value is None or latest.period_start is None:
            return self._insufficient_section("Unemployed Persons", "bls.cps.unemployed_level")

        value = latest.numeric_value
        period_str = f"{latest.period_start.year}-{latest.period_start.month:02d}"
        input_ref = {"type": "observation", "id": latest.id}

        dm = self.repo.add_derived_metric(
            derivation_key=f"insights:unemp_level:{period_str}",
            formula_name="latest_observation",
            formula_version="latest_obs/v1",
            metric="bls.cps.unemployed_level",
            value_text=f"{value:,.0f}K",
            unit="thousands",
            numeric_value=float(value),
            input_refs=[input_ref],
            scope={"geography": "US", "period": period_str},
            caveats=["Seasonally adjusted. In thousands."],
        )

        claim = self.repo.add_claim(
            claim_key=f"insights:unemp_level:{period_str}",
            text=f"U.S. unemployed persons: {value:,.0f} thousand in {period_str} (SA).",
            kind=ClaimKind.REPORTED,
            status=ClaimStatus.SUPPORTED,
            scope={"geography": "US", "period": period_str},
        )
        self.repo.add_evidence(
            claim_id=claim.id,
            evidence_type=EvidenceType.OBSERVATION,
            evidence_id=latest.id,
            relation=EvidenceRelation.SUPPORTS,
        )

        return ReportSection(
            title="U.S. Unemployed Persons (Latest)",
            metric_name="bls.cps.unemployed_level",
            value=f"{value:,.0f}K",
            unit="thousands",
            period=period_str,
            status="computed",
            caveats=("Seasonally adjusted. In thousands.",),
            derived_metric_id=dm.id,
            claim_id=claim.id,
        )

    def _compute_labor_force(
        self, obs: list[Observation], year: int, month: int
    ) -> ReportSection | None:
        """Latest civilian labor force."""
        lf_obs = [o for o in obs if o.metric == "bls.cps.LNS11000000"]
        latest = self._latest_numeric(lf_obs, year, month)
        if latest is None or latest.numeric_value is None or latest.period_start is None:
            return self._insufficient_section("Civilian Labor Force", "bls.cps.labor_force")

        value = latest.numeric_value
        period_str = f"{latest.period_start.year}-{latest.period_start.month:02d}"
        input_ref = {"type": "observation", "id": latest.id}

        dm = self.repo.add_derived_metric(
            derivation_key=f"insights:labor_force:{period_str}",
            formula_name="latest_observation",
            formula_version="latest_obs/v1",
            metric="bls.cps.labor_force",
            value_text=f"{value:,.0f}K",
            unit="thousands",
            numeric_value=float(value),
            input_refs=[input_ref],
            scope={"geography": "US", "period": period_str},
            caveats=["Seasonally adjusted. Civilian noninstitutional population."],
        )

        claim = self.repo.add_claim(
            claim_key=f"insights:labor_force:{period_str}",
            text=f"U.S. civilian labor force: {value:,.0f} thousand in {period_str} (SA).",
            kind=ClaimKind.REPORTED,
            status=ClaimStatus.SUPPORTED,
            scope={"geography": "US", "period": period_str},
        )
        self.repo.add_evidence(
            claim_id=claim.id,
            evidence_type=EvidenceType.OBSERVATION,
            evidence_id=latest.id,
            relation=EvidenceRelation.SUPPORTS,
        )

        return ReportSection(
            title="U.S. Civilian Labor Force (Latest)",
            metric_name="bls.cps.labor_force",
            value=f"{value:,.0f}K",
            unit="thousands",
            period=period_str,
            status="computed",
            caveats=("Seasonally adjusted. Civilian noninstitutional population.",),
            derived_metric_id=dm.id,
            claim_id=claim.id,
        )

    def _compute_qwi_employment(
        self, obs: list[Observation], year: int
    ) -> ReportSection | None:
        """Latest QWI Michigan employment."""
        if not obs:
            return self._insufficient_section("Michigan QWI Employment", "qwi.mi_employment")

        # Get the most recent observation
        latest = max(obs, key=lambda o: o.period_start or date.min)
        if latest.numeric_value is None or latest.period_start is None:
            return self._insufficient_section("Michigan QWI Employment", "qwi.mi_employment")

        value = latest.numeric_value
        period_str = f"{latest.period_start.year}-Q{(latest.period_start.month - 1) // 3 + 1}"
        input_ref = {"type": "observation", "id": latest.id}

        dm = self.repo.add_derived_metric(
            derivation_key=f"insights:qwi_mi_emp:{period_str}",
            formula_name="latest_observation",
            formula_version="latest_obs/v1",
            metric="qwi.mi_employment",
            value_text=f"{value:,.0f}",
            unit="persons",
            numeric_value=float(value),
            input_refs=[input_ref],
            scope={"geography": "MI", "period": period_str},
            caveats=["Latest stored QWI quarter; not necessarily the latest official release. Historical coverage may be incomplete."],
        )

        claim = self.repo.add_claim(
            claim_key=f"insights:qwi_mi_emp:{period_str}",
            text=f"Michigan QWI beginning-of-quarter employment: {value:,.0f} persons in {period_str}.",
            kind=ClaimKind.REPORTED,
            status=ClaimStatus.SUPPORTED,
            scope={"geography": "MI", "period": period_str},
        )
        self.repo.add_evidence(
            claim_id=claim.id,
            evidence_type=EvidenceType.OBSERVATION,
            evidence_id=latest.id,
            relation=EvidenceRelation.SUPPORTS,
        )

        return ReportSection(
            title="Michigan QWI Employment (Latest)",
            metric_name="qwi.mi_employment",
            value=f"{value:,.0f}",
            unit="persons",
            period=period_str,
            status="computed",
            caveats=("Latest stored QWI quarter; not necessarily the latest official release. Historical coverage may be incomplete.",),
            derived_metric_id=dm.id,
            claim_id=claim.id,
        )

    def _compute_qwi_employment_yoy(
        self, obs: list[Observation], year: int
    ) -> ReportSection | None:
        """QWI Michigan employment YoY change."""
        if not obs:
            return self._insufficient_section("Michigan QWI Employment YoY", "qwi.mi_emp_yoy")

        # Find latest and same-quarter-prior-year
        latest = max(obs, key=lambda o: o.period_start or date.min)
        if latest.period_start is None or latest.numeric_value is None:
            return self._insufficient_section("Michigan QWI Employment YoY", "qwi.mi_emp_yoy")

        target_quarter = (latest.period_start.month - 1) // 3 + 1
        prior_year = latest.period_start.year - 1
        prior_obs = [
            o
            for o in obs
            if o.period_start is not None
            and o.numeric_value is not None
            and o.period_start.year == prior_year
            and (o.period_start.month - 1) // 3 + 1 == target_quarter
        ]
        if not prior_obs:
            return self._insufficient_section("Michigan QWI Employment YoY", "qwi.mi_emp_yoy")

        prior = prior_obs[0]
        if prior.numeric_value is None:
            return self._insufficient_section("Michigan QWI Employment YoY", "qwi.mi_emp_yoy")
        change = latest.numeric_value - prior.numeric_value
        change_pct = (change / prior.numeric_value * 100) if prior.numeric_value else 0.0
        period_str = f"{latest.period_start.year}-Q{target_quarter}"
        input_refs = [
            {"type": "observation", "id": latest.id},
            {"type": "observation", "id": prior.id},
        ]

        dm = self.repo.add_derived_metric(
            derivation_key=f"insights:qwi_mi_emp_yoy:{period_str}",
            formula_name="yoy_change",
            formula_version="yoy/v1",
            metric="qwi.mi_employment_yoy",
            value_text=f"{change:+,.0f} ({change_pct:+.1f}%)",
            unit="persons",
            numeric_value=float(change),
            input_refs=input_refs,
            scope={"geography": "MI", "period": period_str},
            caveats=["Historical QWI comparison for the same quarter; not a current Michigan workforce estimate."],
        )

        direction = "increased" if change > 0 else "decreased"
        claim = self.repo.add_claim(
            claim_key=f"insights:qwi_mi_emp_yoy:{period_str}",
            text=(
                f"Michigan QWI employment {direction} by {abs(change):,.0f} "
                f"({abs(change_pct):.1f}%) year-over-year "
                f"({prior.numeric_value:,.0f} in {prior_year}-Q{target_quarter} → "
                f"{latest.numeric_value:,.0f} in {period_str})."
            ),
            kind=ClaimKind.DERIVED,
            status=ClaimStatus.SUPPORTED,
            scope={"geography": "MI", "period": period_str},
        )
        self.repo.add_evidence(
            claim_id=claim.id,
            evidence_type=EvidenceType.DERIVED_METRIC,
            evidence_id=dm.id,
            relation=EvidenceRelation.DERIVES_FROM,
        )

        return ReportSection(
            title="Michigan QWI Employment YoY Change",
            metric_name="qwi.mi_employment_yoy",
            value=f"{change:+,.0f} ({change_pct:+.1f}%)",
            unit="persons",
            period=period_str,
            status="computed",
            caveats=("Historical QWI comparison for the same quarter; not a current Michigan workforce estimate.",),
            derived_metric_id=dm.id,
            claim_id=claim.id,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _latest_numeric(
        self, obs: list[Observation], year: int, month: int
    ) -> Observation | None:
        """Find the most recent observation with a numeric value up to the given month."""
        candidates = [
            o
            for o in obs
            if o.numeric_value is not None
            and o.period_start is not None
            and o.period_start.year <= year
            and (o.period_start.year < year or o.period_start.month <= month)
        ]
        if not candidates:
            return None

        def _period_key(o: Observation) -> date:
            assert o.period_start is not None
            return o.period_start

        return max(candidates, key=_period_key)

    def _insufficient_section(self, title: str, metric_name: str) -> ReportSection:
        return ReportSection(
            title=title,
            metric_name=metric_name,
            value="N/A",
            unit="",
            period="",
            status="insufficient_data",
            caveats=("No data available for the requested period.",),
        )

    def _compute_coverage(
        self, bls_obs: list[Observation], qwi_obs: list[Observation], year: int
    ) -> dict[str, Any]:
        """Summarize data coverage for the report."""
        bls_series = {o.metric for o in bls_obs}
        qwi_count = len(qwi_obs)

        return {
            "bls_cps_observations": len(bls_obs),
            "bls_cps_series": sorted(bls_series),
            "qwi_observations": qwi_count,
            "qwi_has_data": qwi_count > 0,
            "report_year": year,
        }
