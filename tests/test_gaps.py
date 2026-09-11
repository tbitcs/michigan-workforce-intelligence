from decimal import Decimal

import pytest

from mijobs.analytics.gaps import (
    ComparableMetric,
    IncompatibleMetricError,
    market_tightness,
    training_pipeline_gap,
)


def metric(name: str, value: str, *, geo: str = "MI", unit: str = "people_per_year") -> ComparableMetric:
    return ComparableMetric(
        name=name,
        value=Decimal(value),
        unit=unit,
        geography_code=geo,
        period_basis="annual",
        taxonomy_system="SOC",
        taxonomy_version="2024",
        taxonomy_code="49-9041",
    )


def test_training_pipeline_gap_with_missing_components() -> None:
    result = training_pipeline_gap(
        annual_openings=metric("openings", "1000"),
        completions=metric("completions", "600"),
        apprenticeship_completions=metric("apprentices", "100"),
    )
    assert result.gap == Decimal("300")
    assert result.classification == "shortage_pressure"
    assert "estimated_transfers_in" in result.missing_components
    assert result.completeness < 1


def test_training_gap_rejects_incompatible_geography() -> None:
    with pytest.raises(IncompatibleMetricError):
        training_pipeline_gap(
            annual_openings=metric("openings", "1000", geo="MI"),
            completions=metric("completions", "600", geo="26163"),
        )


def test_training_gap_rejects_job_postings_as_annual_people() -> None:
    with pytest.raises(IncompatibleMetricError):
        training_pipeline_gap(
            annual_openings=metric("openings", "1000"),
            completions=metric("ads", "600", unit="job_ads"),
        )


def test_market_tightness_keeps_caveat() -> None:
    result = market_tightness(online_job_ads=Decimal("100"), available_people=Decimal("115"))
    assert result.available_people_per_100_postings == Decimal("115")
    assert any("not unique vacancies" in caveat for caveat in result.caveats)
