"""Transparent monthly reference outlooks; no causal or official forecast claims."""

from __future__ import annotations

import math
from datetime import date
from typing import Any


def monthly_outlook(
    points: list[dict[str, Any]], *, unit: str, horizon: int = 12
) -> dict[str, Any]:
    if not 1 <= horizon <= 12:
        raise ValueError("Horizon must be 1-12 months")
    rows: list[tuple[int, float, dict[str, Any]]] = []
    for p in points:
        value = p.get("value")
        if value is None:
            continue
        try:
            stamp = date.fromisoformat(str(p.get("date") or p.get("period_start")))
        except ValueError:
            return {"status": "unsupported", "reason": "Missing or invalid observation date"}
        number = float(value)
        if number < 0 or (unit == "percent" and number > 100):
            return {"status": "unsupported", "reason": "Input outside supported measurement bounds"}
        if not math.isfinite(number):
            return {"status": "unsupported", "reason": "Non-finite input"}
        rows.append((stamp.year * 12 + stamp.month - 1, number, p))
    rows.sort(key=lambda r: r[0])
    if len({r[0] for r in rows}) != len(rows):
        return {
            "status": "unsupported",
            "reason": "Multiple observations in a month; select one compatible series",
        }
    if len(rows) < 36 or rows[-1][0] - rows[0][0] < 35:
        return {"status": "unsupported", "reason": "At least 36 monthly observations required"}
    if rows[-1][0] - rows[-24][0] > 30:
        return {
            "status": "unsupported",
            "reason": "Recent coverage too sparse for monthly reference outlook",
        }

    def predict(train: list[tuple[int, float, dict[str, Any]]], steps: int, drift: bool) -> float:
        last = train[-1]
        earlier = train[max(0, len(train) - 25)]
        slope = (last[1] - earlier[1]) / (last[0] - earlier[0]) if drift else 0.0
        result = last[1] + slope * sum(0.8**i for i in range(steps))
        return min(100.0, max(0.0, result)) if unit == "percent" else max(0.0, result)

    errors: dict[str, list[float]] = {"persistence": [], "damped_drift": []}
    for i in range(len(rows) - 12, len(rows)):
        for method in errors:
            guess = predict(rows[:i], rows[i][0] - rows[i - 1][0], method == "damped_drift")
            errors[method].append(abs(guess - rows[i][1]))
    mae = {method: sum(values) / len(values) for method, values in errors.items()}
    selected = min(mae, key=lambda k: mae[k])
    scale = max(errors[selected])
    forecasts = []
    for step in range(1, horizon + 1):
        month = rows[-1][0] + step
        center = predict(rows, step, selected == "damped_drift")
        width = scale * math.sqrt(step)
        forecasts.append(
            {
                "date": f"{month // 12:04d}-{month % 12 + 1:02d}-01",
                "value": center,
                "scenario_low": max(0.0, center - width),
                "scenario_high": min(100.0, center + width)
                if unit == "percent"
                else center + width,
            }
        )
    return {
        "status": "reference_outlook",
        "method": selected,
        "unit": unit,
        "last_observed": rows[-1][2],
        "rolling_holdout_observations": 12,
        "rolling_holdout_mae": mae,
        "forecast": forecasts,
        "input_observation_ids": [r[2].get("observation_id") for r in rows],
        "limitations": [
            "Calendar gaps are preserved; missing observations are not imputed.",
            "Model selection and error estimates use the same rolling holdout; no independent validation set.",
            "Ranges are stress scenarios based on maximum holdout error scaled by square root of horizon, not confidence intervals.",
            "No causal explanation, policy effect, employer layoff probability, seasonal model, or structural break adjustment is estimated.",
            "Review input vintage and population-control changes before operational decisions.",
        ],
    }
