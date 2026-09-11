from __future__ import annotations

from decimal import Decimal

import pytest

from mijobs.analytics.policy import (
    TrainingPolicyAssumptions,
    assumptions_from_mapping,
    evaluate_training_policy,
    evaluate_training_policy_sensitivity,
)


def _assumptions(
    *,
    completion: str = "0.80",
    placement: str = "0.75",
    retention: str = "0.90",
    counterfactual: str = "0.25",
) -> TrainingPolicyAssumptions:
    return TrainingPolicyAssumptions(
        annual_training_seats=Decimal("100"),
        cost_per_seat=Decimal("10000"),
        completion_rate=Decimal(completion),
        placement_rate=Decimal(placement),
        michigan_retention_rate=Decimal(retention),
        counterfactual_entry_share=Decimal(counterfactual),
    )


def test_training_policy_calculates_net_additionality_and_cost() -> None:
    result = evaluate_training_policy(
        baseline_gap_workers=Decimal("100"),
        assumptions=_assumptions(),
    )
    assert result.completers == Decimal("80")
    assert result.placed_workers == Decimal("60")
    assert result.michigan_retained_workers == Decimal("54")
    assert result.net_additional_workers == Decimal("40.50")
    assert result.residual_gap_workers == Decimal("59.50")
    assert result.gap_closed_share == Decimal("0.405")
    assert result.annual_program_cost == Decimal("1000000")
    assert result.cost_per_net_additional_worker == Decimal("1000000") / Decimal("40.50")
    assert "conditional" in result.caveats[0]


def test_training_policy_handles_zero_gap_and_zero_additionality() -> None:
    result = evaluate_training_policy(
        baseline_gap_workers=Decimal("0"),
        assumptions=_assumptions(counterfactual="1"),
    )
    assert result.net_additional_workers == Decimal("0")
    assert result.residual_gap_workers == Decimal("0")
    assert result.gap_closed_share is None
    assert result.cost_per_net_additional_worker is None


def test_training_policy_validates_rates_and_nonnegative_values() -> None:
    with pytest.raises(ValueError, match="completion_rate"):
        evaluate_training_policy(
            baseline_gap_workers=Decimal("10"),
            assumptions=_assumptions(completion="1.1"),
        )
    with pytest.raises(ValueError, match="baseline_gap_workers"):
        evaluate_training_policy(
            baseline_gap_workers=Decimal("-1"),
            assumptions=_assumptions(),
        )
    with pytest.raises(ValueError, match="annual_training_seats"):
        evaluate_training_policy(
            baseline_gap_workers=Decimal("10"),
            assumptions=TrainingPolicyAssumptions(
                annual_training_seats=Decimal("-1"),
                cost_per_seat=Decimal("1"),
                completion_rate=Decimal("1"),
                placement_rate=Decimal("1"),
                michigan_retention_rate=Decimal("1"),
                counterfactual_entry_share=Decimal("0"),
            ),
        )


def test_sensitivity_uses_explicit_assumption_sets() -> None:
    result = evaluate_training_policy_sensitivity(
        baseline_gap_workers=Decimal("100"),
        low=_assumptions(completion="0.5"),
        base=_assumptions(completion="0.8"),
        high=_assumptions(completion="1"),
    )
    assert result.low.net_additional_workers < result.base.net_additional_workers
    assert result.base.net_additional_workers < result.high.net_additional_workers


def test_assumptions_from_mapping_requires_every_parameter() -> None:
    with pytest.raises(ValueError, match="missing policy assumptions"):
        assumptions_from_mapping({"annual_training_seats": 100})
    parsed = assumptions_from_mapping(
        {
            "annual_training_seats": 100,
            "cost_per_seat": 5000,
            "completion_rate": 0.8,
            "placement_rate": 0.7,
            "michigan_retention_rate": 0.9,
            "counterfactual_entry_share": 0.2,
        }
    )
    assert parsed.cost_per_seat == Decimal("5000")
