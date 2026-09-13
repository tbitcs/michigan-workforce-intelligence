"""Recompute this report's illustrative assumptions using Python's standard library."""

import json
from pathlib import Path

workers = 200
cash_items = {
    "training_200_times_2500": 200 * 2500,
    "four_fte_loaded_100000_each": 4 * 100000,
    "supports_200_times_800": 200 * 800,
    "flexible_bridge_80_times_1500": 80 * 1500,
    "data_legal_independent_evaluation": 100000,
}
subtotal = sum(cash_items.values())
contingency = subtotal // 10
cash = subtotal + contingency
paid_time = workers * 80 * 30
economic = cash + paid_time
scenarios = {}
for name, sustained, days, gainers, hourly_gain in [
    ("low", 110, 30, 20, 2),
    ("base", 140, 18, 50, 3),
    ("high", 170, 8, 80, 4),
]:
    additional = sustained - 90
    days_avoided = workers * (45 - days)
    scenarios[name] = {
        "workers": workers,
        "six_month_sustained_with_program": sustained,
        "assumed_sustained_without_program": 90,
        "additional_sustained_outcomes": additional,
        "mean_unemployment_days_with_program": days,
        "assumed_mean_days_without_program": 45,
        "aggregate_unemployment_days_avoided": days_avoided,
        "workers_with_hourly_gain": gainers,
        "hourly_gain_dollars": hourly_gain,
        "annualized_gross_wage_gain_at_2080_hours": gainers * hourly_gain * 2080,
        "cash_cost_per_sustained": round(cash / sustained, 2),
        "cash_cost_per_additional_sustained": round(cash / additional, 2),
        "economic_cost_per_additional_sustained": round(economic / additional, 2),
        "cash_cost_per_unemployment_day_avoided": round(cash / days_avoided, 2),
    }
model = {
    "schema": "michigan-job-continuity-scenario/v1",
    "as_of": "2026-09-13",
    "status": "illustrative assumptions, not estimated effects or funding awards",
    "core_workers": workers,
    "cash_items": cash_items,
    "cash_subtotal": subtotal,
    "contingency_10_percent": contingency,
    "total_cash": cash,
    "employer_paid_training_time_200_times_80_hours_times_30_loaded": paid_time,
    "total_economic_resources": economic,
    "committed_grant_revenue": 0,
    "scenarios": scenarios,
    "optional_students": {
        "people_excluded_from_core": 40,
        "paid_hours_each": 240,
        "hourly_wage_assumption": 22,
        "gross_wages": 40 * 240 * 22,
        "payroll_load_assumption_20_percent": 40 * 240 * 22 // 5,
        "coordination_and_support": 40000,
        "additional_total": 40 * 240 * 22 * 6 // 5 + 40000,
    },
    "optional_job_corps": {
        "people_excluded_from_core_and_students": 30,
        "local_cash_assumption": 93500,
        "federal_training_and_residence_cost": None,
        "sustained_outcomes_low_base_high": [10, 18, 24],
        "counterfactual_outcomes_low_base_high": [8, 10, 12],
        "additional_outcomes_low_base_high": [2, 8, 12],
        "cost_per_additional_outcome_low_base_high": [46750, 11687.5, 7791.666667],
        "combined_local_cash_with_core_and_students": cash + 293440 + 93500,
        "combined_economic_resources_excluding_unknown_federal_cost": economic + 293440 + 93500,
    },
    "limits": [
        "Six-month outcomes are distinct from twelve-month retention.",
        "The control assumptions are not observed in the database.",
        "Wage gains are annualized at full-time hours, not realized year-one benefits.",
        "Do not add wage gains and unemployment-day values into a benefit total.",
        "Training cost is a blended allowance, not a quoted course price.",
        "UI payments, ordinary productive wages and inbound relocation are excluded.",
    ],
}
Path(__file__).with_name("scenario-model.json").write_text(
    json.dumps(model, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"cash": cash, "economic": economic, "scenarios": scenarios}, indent=2))
