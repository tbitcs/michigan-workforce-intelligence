from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class TrainingPolicyAssumptions:
    """Explicit assumptions for one workforce-training intervention.

    The model intentionally does not infer causal parameters. Every rate is caller-supplied
    and should be tied to evidence or clearly labeled as a scenario assumption upstream.
    """

    annual_training_seats: Decimal
    cost_per_seat: Decimal
    completion_rate: Decimal
    placement_rate: Decimal
    michigan_retention_rate: Decimal
    counterfactual_entry_share: Decimal


@dataclass(frozen=True, slots=True)
class TrainingPolicyResult:
    baseline_gap_workers: Decimal
    annual_training_seats: Decimal
    completers: Decimal
    placed_workers: Decimal
    michigan_retained_workers: Decimal
    net_additional_workers: Decimal
    residual_gap_workers: Decimal
    gap_closed_share: Decimal | None
    annual_program_cost: Decimal
    cost_per_net_additional_worker: Decimal | None
    assumptions: dict[str, str]
    caveats: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    low: TrainingPolicyResult
    base: TrainingPolicyResult
    high: TrainingPolicyResult


def _validate_nonnegative(name: str, value: Decimal) -> None:
    if value < ZERO:
        raise ValueError(f"{name} must be >= 0")


def _validate_rate(name: str, value: Decimal) -> None:
    if value < ZERO or value > ONE:
        raise ValueError(f"{name} must be in [0,1]")


def evaluate_training_policy(
    *,
    baseline_gap_workers: Decimal,
    assumptions: TrainingPolicyAssumptions,
) -> TrainingPolicyResult:
    """Evaluate a narrow training-pipeline intervention with explicit counterfactuals.

    ``counterfactual_entry_share`` is the share of retained placed workers assumed to have
    entered the target occupation in Michigan even without the intervention. Subtracting it
    prevents the scenario from automatically treating every program outcome as additional.
    """

    _validate_nonnegative("baseline_gap_workers", baseline_gap_workers)
    _validate_nonnegative("annual_training_seats", assumptions.annual_training_seats)
    _validate_nonnegative("cost_per_seat", assumptions.cost_per_seat)
    for name in (
        "completion_rate",
        "placement_rate",
        "michigan_retention_rate",
        "counterfactual_entry_share",
    ):
        _validate_rate(name, getattr(assumptions, name))

    completers = assumptions.annual_training_seats * assumptions.completion_rate
    placed = completers * assumptions.placement_rate
    retained = placed * assumptions.michigan_retention_rate
    additionality = ONE - assumptions.counterfactual_entry_share
    net_additional = retained * additionality
    residual = max(ZERO, baseline_gap_workers - net_additional)
    gap_closed = None
    if baseline_gap_workers > ZERO:
        gap_closed = min(ONE, net_additional / baseline_gap_workers)
    annual_cost = assumptions.annual_training_seats * assumptions.cost_per_seat
    cost_per_worker = None if net_additional == ZERO else annual_cost / net_additional

    return TrainingPolicyResult(
        baseline_gap_workers=baseline_gap_workers,
        annual_training_seats=assumptions.annual_training_seats,
        completers=completers,
        placed_workers=placed,
        michigan_retained_workers=retained,
        net_additional_workers=net_additional,
        residual_gap_workers=residual,
        gap_closed_share=gap_closed,
        annual_program_cost=annual_cost,
        cost_per_net_additional_worker=cost_per_worker,
        assumptions={key: str(value) for key, value in asdict(assumptions).items()},
        caveats=(
            "Scenario result is conditional on caller-supplied assumptions; it is not a causal estimate.",
            "The model does not include wage responses, migration, employer substitution, induced demand, or macroeconomic multipliers.",
            "Do not interpret program placements as net new workers without an evidence-backed counterfactual entry share.",
        ),
    )


def evaluate_training_policy_sensitivity(
    *,
    baseline_gap_workers: Decimal,
    low: TrainingPolicyAssumptions,
    base: TrainingPolicyAssumptions,
    high: TrainingPolicyAssumptions,
) -> SensitivityResult:
    """Evaluate explicit low/base/high assumption sets without inventing ranges."""

    return SensitivityResult(
        low=evaluate_training_policy(
            baseline_gap_workers=baseline_gap_workers,
            assumptions=low,
        ),
        base=evaluate_training_policy(
            baseline_gap_workers=baseline_gap_workers,
            assumptions=base,
        ),
        high=evaluate_training_policy(
            baseline_gap_workers=baseline_gap_workers,
            assumptions=high,
        ),
    )


def assumptions_from_mapping(payload: dict[str, Any]) -> TrainingPolicyAssumptions:
    required = (
        "annual_training_seats",
        "cost_per_seat",
        "completion_rate",
        "placement_rate",
        "michigan_retention_rate",
        "counterfactual_entry_share",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"missing policy assumptions: {', '.join(missing)}")
    return TrainingPolicyAssumptions(
        annual_training_seats=Decimal(str(payload["annual_training_seats"])),
        cost_per_seat=Decimal(str(payload["cost_per_seat"])),
        completion_rate=Decimal(str(payload["completion_rate"])),
        placement_rate=Decimal(str(payload["placement_rate"])),
        michigan_retention_rate=Decimal(str(payload["michigan_retention_rate"])),
        counterfactual_entry_share=Decimal(str(payload["counterfactual_entry_share"])),
    )
