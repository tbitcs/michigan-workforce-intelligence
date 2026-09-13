from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


class IncompatibleMetricError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ComparableMetric:
    name: str
    value: Decimal
    unit: str
    geography_code: str
    period_basis: str
    taxonomy_system: str
    taxonomy_version: str
    taxonomy_code: str
    source_observation_id: str | None = None


@dataclass(frozen=True, slots=True)
class GapResult:
    formula_version: str
    demand: Decimal
    known_supply: Decimal
    gap: Decimal
    classification: str
    included_components: tuple[str, ...]
    missing_components: tuple[str, ...]
    completeness: Decimal
    caveats: tuple[str, ...]


def _validate_same_basis(metrics: Iterable[ComparableMetric], expected_unit: str) -> None:
    items = list(metrics)
    if not items:
        raise ValueError("at least one metric is required")
    anchor = items[0]
    for metric in items:
        if metric.unit != expected_unit:
            raise IncompatibleMetricError(
                f"{metric.name} unit {metric.unit!r} is not {expected_unit!r}"
            )
        for field in (
            "geography_code",
            "period_basis",
            "taxonomy_system",
            "taxonomy_version",
            "taxonomy_code",
        ):
            if getattr(metric, field) != getattr(anchor, field):
                raise IncompatibleMetricError(
                    f"{metric.name} is incompatible on {field}: "
                    f"{getattr(metric, field)!r} != {getattr(anchor, field)!r}"
                )


def training_pipeline_gap(
    *,
    annual_openings: ComparableMetric,
    completions: ComparableMetric,
    apprenticeship_completions: ComparableMetric | None = None,
    estimated_transfers_in: ComparableMetric | None = None,
    other_known_supply: ComparableMetric | None = None,
) -> GapResult:
    """Compute a narrow training/supply pipeline gap without double-counting job ads.

    This is deliberately not a total labor-shortage estimate. It compares annual
    projected openings with explicitly annualized, occupation-compatible supply components.
    """

    optional = {
        "apprenticeship_completions": apprenticeship_completions,
        "estimated_transfers_in": estimated_transfers_in,
        "other_known_supply": other_known_supply,
    }
    present = [annual_openings, completions, *[value for value in optional.values() if value]]
    _validate_same_basis(present, "people_per_year")
    if annual_openings.value < 0 or completions.value < 0:
        raise ValueError("demand and supply components cannot be negative")

    known_supply = completions.value + sum(
        (value.value for value in optional.values() if value is not None), Decimal("0")
    )
    gap = annual_openings.value - known_supply
    classification = "shortage_pressure" if gap > 0 else "pipeline_meets_or_exceeds_openings"
    included = ("annual_openings", "completions",
        *(key for key, value in optional.items() if value is not None)
    )
    missing = tuple(key for key, value in optional.items() if value is None)
    completeness = Decimal(len(included)) / Decimal(2 + len(optional))
    return GapResult(
        formula_version="training_pipeline_gap/v1",
        demand=annual_openings.value,
        known_supply=known_supply,
        gap=gap,
        classification=classification,
        included_components=included,
        missing_components=missing,
        completeness=completeness,
        caveats=(
            "This is a pipeline comparison, not proof of a realized labor shortage.",
            "Completions do not imply Michigan labor-force entry or occupation match.",
            "Projected openings can include replacement demand and are model-based.",
        ),
    )


@dataclass(frozen=True, slots=True)
class MarketTightnessResult:
    formula_version: str
    postings_per_available_person: Decimal | None
    available_people_per_100_postings: Decimal | None
    interpretation: str
    caveats: tuple[str, ...]


def market_tightness(
    *,
    online_job_ads: Decimal,
    available_people: Decimal,
) -> MarketTightnessResult:
    if online_job_ads < 0 or available_people < 0:
        raise ValueError("counts cannot be negative")
    if online_job_ads == 0:
        return MarketTightnessResult(
            "market_tightness/v1",
            None,
            None,
            "undefined_no_postings",
            ("Online job advertisements are not a census of unique vacancies.",),
        )
    postings_per_person = online_job_ads / available_people if available_people else None
    people_per_100 = (available_people / online_job_ads) * Decimal("100")
    if available_people == 0:
        interpretation = "extremely_tight_or_supply_measure_incomplete"
    elif people_per_100 < 100:
        interpretation = "fewer_available_people_than_ads"
    else:
        interpretation = "available_people_at_least_as_numerous_as_ads"
    return MarketTightnessResult(
        "market_tightness/v1",
        postings_per_person,
        people_per_100,
        interpretation,
        (
            "Online job advertisements are not unique vacancies or hires.",
            "Available people must be defined consistently; total unemployed is not the same as qualified occupational supply.",
        ),
    )
