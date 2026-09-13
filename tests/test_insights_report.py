"""Tests for the insights report generator."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from mijobs.domain import ObservationInput
from mijobs.insights_report import InsightsReport, InsightsReportGenerator, ReportSection
from mijobs.repository import EvidenceRepository


def _seed_bls_obs(
    repo: EvidenceRepository,
    metric: str,
    values: list[tuple[date, float]],
) -> list[str]:
    """Seed BLS CPS observations and return their IDs."""
    artifact = repo.add_source_artifact(
        source_id="us_bls_api",
        source_locator=f"https://api.bls.gov/v2/{metric}",
        retrieved_at=datetime(2026, 9, 1, tzinfo=UTC),
        content_sha256="a" * 64,
        media_type="application/json",
        byte_size=100,
        local_path=f"aa/{metric}",
    )
    ids: list[str] = []
    for period_start, value in values:
        obs = repo.add_observation(
            artifact.id,
            ObservationInput(
                observation_key=f"bls:{metric}:{period_start.year}:{period_start.month:02d}",
                metric=metric,
                value_text=str(value),
                numeric_value=Decimal(str(value)),
                unit="percent" if "rate" in metric else "thousands",
                geography_type="national",
                geography_code="US",
                period_start=period_start,
                period_end=period_start,
                period_basis="monthly",
            ),
        )
        ids.append(obs.id)
    return ids


def _seed_qwi_obs(
    repo: EvidenceRepository,
    values: list[tuple[date, float]],
) -> list[str]:
    """Seed QWI Michigan employment observations."""
    artifact = repo.add_source_artifact(
        source_id="us_census_qwi",
        source_locator="https://api.census.gov/data/qwi/sa/state:26",
        retrieved_at=datetime(2026, 9, 1, tzinfo=UTC),
        content_sha256="b" * 64,
        media_type="application/json",
        byte_size=200,
        local_path="bb/qwi",
    )
    ids: list[str] = []
    for period_start, value in values:
        quarter = (period_start.month - 1) // 3 + 1
        obs = repo.add_observation(
            artifact.id,
            ObservationInput(
                observation_key=f"qwi:state:26:{period_start.year}-Q{quarter}",
                metric="qwi.Emp",
                value_text=str(int(value)),
                numeric_value=Decimal(str(int(value))),
                unit="persons",
                geography_type="state",
                geography_code="26",
                period_start=period_start,
                period_end=period_start,
                period_basis="quarterly",
            ),
        )
        ids.append(obs.id)
    return ids


@pytest.fixture
def seeded_session(db_session: Session) -> Session:
    """Session with BLS and QWI observations pre-seeded."""
    repo = EvidenceRepository(db_session, actor="test")

    # Unemployment rate: 2025-08 (4.4%), 2026-08 (4.1%)
    _seed_bls_obs(
        repo,
        "bls.cps.LNS14000000",
        [(date(2025, 8, 1), 4.4), (date(2026, 8, 1), 4.1)],
    )
    # Unemployed level: 2025-08 (7,000K), 2026-08 (6,800K)
    _seed_bls_obs(
        repo,
        "bls.cps.LNS13000000",
        [(date(2025, 8, 1), 7000.0), (date(2026, 8, 1), 6800.0)],
    )
    # Labor force: 2025-08 (168,000K), 2026-08 (169,000K)
    _seed_bls_obs(
        repo,
        "bls.cps.LNS11000000",
        [(date(2025, 8, 1), 168000.0), (date(2026, 8, 1), 169000.0)],
    )
    # QWI: 2020-Q4 (4,120,000), 2021-Q1 (4,200,000), 2021-Q4 (4,160,099)
    _seed_qwi_obs(
        repo,
        [
            (date(2020, 10, 1), 4120000.0),
            (date(2021, 1, 1), 4200000.0),
            (date(2021, 10, 1), 4160099.0),
        ],
    )
    db_session.flush()
    return db_session


class TestInsightsReportGenerator:
    def test_generate_full_report(self, seeded_session: Session) -> None:
        gen = InsightsReportGenerator(seeded_session, actor="test")
        report = gen.generate(as_of=date(2026, 8, 15))

        assert isinstance(report, InsightsReport)
        assert report.reporting_period == "2026-08"
        assert report.ledger_valid is True
        assert len(report.sections) == 6

        # Section 1: Unemployment rate
        s = report.sections[0]
        assert s.status == "computed"
        assert s.value == "4.1%"
        assert s.period == "2026-08"
        assert s.derived_metric_id is not None
        assert s.claim_id is not None

        # Section 2: YoY change
        s = report.sections[1]
        assert s.status == "computed"
        assert "-0.3" in s.value
        assert s.period == "2026-08"

        # Section 3: Unemployed level
        s = report.sections[2]
        assert s.status == "computed"
        assert "6,800" in s.value
        assert s.unit == "thousands"

        # Section 4: Labor force
        s = report.sections[3]
        assert s.status == "computed"
        assert "169,000" in s.value

        # Section 5: QWI employment
        s = report.sections[4]
        assert s.status == "computed"
        assert "4,160,099" in s.value
        assert s.period == "2021-Q4"

        # Section 6: QWI YoY
        s = report.sections[5]
        assert s.status == "computed"
        # 4,160,099 - 4,120,000 = +40,099
        assert "+40,099" in s.value

    def test_generate_empty_db(self, db_session: Session) -> None:
        gen = InsightsReportGenerator(db_session, actor="test")
        report = gen.generate(as_of=date(2026, 8, 15))

        assert report.reporting_period == "2026-08"
        # All sections should be insufficient_data
        for section in report.sections:
            assert section.status == "insufficient_data"
            assert section.value == "N/A"

    def test_generate_no_qwi_data(self, db_session: Session) -> None:
        repo = EvidenceRepository(db_session, actor="test")
        # Only BLS data, no QWI
        _seed_bls_obs(
            repo,
            "bls.cps.LNS14000000",
            [(date(2026, 8, 1), 4.1)],
        )
        db_session.flush()

        gen = InsightsReportGenerator(db_session, actor="test")
        report = gen.generate(as_of=date(2026, 8, 15))

        # QWI sections should be insufficient
        assert report.sections[4].status == "insufficient_data"
        assert report.sections[5].status == "insufficient_data"
        # BLS sections should be computed (but YoY needs prior year)
        assert report.sections[0].status == "computed"

    def test_generate_no_prior_year_for_yoy(self, db_session: Session) -> None:
        repo = EvidenceRepository(db_session, actor="test")
        # Only current year data — no prior year for YoY
        _seed_bls_obs(
            repo,
            "bls.cps.LNS14000000",
            [(date(2026, 8, 1), 4.1)],
        )
        db_session.flush()

        gen = InsightsReportGenerator(db_session, actor="test")
        report = gen.generate(as_of=date(2026, 8, 15))

        # YoY should be insufficient (no 2025 data)
        assert report.sections[1].status == "insufficient_data"

    def test_to_dict_schema(self, seeded_session: Session) -> None:
        gen = InsightsReportGenerator(seeded_session, actor="test")
        report = gen.generate(as_of=date(2026, 8, 15))
        d = report.to_dict()

        assert d["schema"] == "mijobs-insights-report/v1"
        assert "generated_at" in d
        assert "reporting_period" in d
        assert "sections" in d
        assert "data_coverage" in d
        assert "ledger_valid" in d
        assert "total_derived_metrics" in d
        assert "total_claims" in d
        assert len(d["sections"]) == 6
        assert d["data_coverage"]["bls_cps_observations"] > 0
        assert d["data_coverage"]["qwi_has_data"] is True

    def test_coverage_summary(self, seeded_session: Session) -> None:
        gen = InsightsReportGenerator(seeded_session, actor="test")
        report = gen.generate(as_of=date(2026, 8, 15))

        coverage = report.data_coverage
        assert coverage["report_year"] == 2026
        assert coverage["qwi_observations"] == 3
        assert "bls.cps.LNS14000000" in coverage["bls_cps_series"]
        assert "bls.cps.LNS13000000" in coverage["bls_cps_series"]
        assert "bls.cps.LNS11000000" in coverage["bls_cps_series"]


class TestReportSection:
    def test_insufficient_section(self) -> None:
        section = ReportSection(
            title="Test",
            metric_name="test.metric",
            value="N/A",
            unit="",
            period="",
            status="insufficient_data",
            caveats=("No data.",),
        )
        assert section.status == "insufficient_data"
        assert section.derived_metric_id is None
        assert section.claim_id is None


class TestLatestNumeric:
    def test_returns_most_recent(self, db_session: Session) -> None:
        repo = EvidenceRepository(db_session, actor="test")
        _seed_bls_obs(
            repo,
            "bls.cps.LNS14000000",
            [(date(2026, 1, 1), 4.0), (date(2026, 6, 1), 4.2), (date(2026, 8, 1), 4.1)],
        )
        db_session.flush()

        gen = InsightsReportGenerator(db_session, actor="test")
        obs = gen._query_bls_observations(2026)
        rate_obs = [o for o in obs if "LNS14000000" in o.metric]
        latest = gen._latest_numeric(rate_obs, 2026, 8)
        assert latest is not None
        assert latest.numeric_value == 4.1
        assert latest.period_start == date(2026, 8, 1)

    def test_respects_month_boundary(self, db_session: Session) -> None:
        repo = EvidenceRepository(db_session, actor="test")
        _seed_bls_obs(
            repo,
            "bls.cps.LNS14000000",
            [(date(2026, 1, 1), 4.0), (date(2026, 8, 1), 4.1), (date(2026, 9, 1), 4.3)],
        )
        db_session.flush()

        gen = InsightsReportGenerator(db_session, actor="test")
        obs = gen._query_bls_observations(2026)
        rate_obs = [o for o in obs if "LNS14000000" in o.metric]
        # As of August, September data should be excluded
        latest = gen._latest_numeric(rate_obs, 2026, 8)
        assert latest is not None
        assert latest.numeric_value == 4.1

    def test_returns_none_when_empty(self, db_session: Session) -> None:
        gen = InsightsReportGenerator(db_session, actor="test")
        assert gen._latest_numeric([], 2026, 8) is None


def test_yoy_uses_actual_observation_month(seeded_session):
    report = InsightsReportGenerator(seeded_session).generate(as_of=date(2026, 9, 13))
    assert report.sections[1].period == '2026-08'
    assert '-0.3' in report.sections[1].value


def test_report_does_not_mislabel_unemployment_as_labor_force(db_session):
    repo = EvidenceRepository(db_session)
    _seed_bls_obs(repo, 'bls.cps.LNS13000000', [(date(2026, 8, 1), 7031)])
    _seed_bls_obs(repo, 'bls.cps.LNU04000000', [(date(2026, 8, 1), 4.3)])
    report = InsightsReportGenerator(db_session).generate(as_of=date(2026, 9, 13))
    assert report.sections[2].value == '7,031K'
    assert report.sections[3].status == 'insufficient_data'


def test_report_uses_latest_revision_and_respects_qwi_as_of(db_session):
    repo = EvidenceRepository(db_session)
    _seed_bls_obs(repo, 'bls.cps.LNS14000000', [(date(2026, 8, 1), 4.1)])
    _seed_bls_obs(repo, 'bls.cps.LNS14000000', [(date(2026, 8, 1), 4.2)])
    _seed_qwi_obs(repo, [(date(2027, 1, 1), 9000000)])
    report = InsightsReportGenerator(db_session).generate(as_of=date(2026, 9, 13))
    assert report.sections[0].value == '4.2%'
    assert report.sections[4].status == 'insufficient_data'
