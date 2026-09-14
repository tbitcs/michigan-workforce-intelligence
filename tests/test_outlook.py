from datetime import date

import pytest

from mijobs.outlook import monthly_outlook


def series(n=60):
    return [
        {
            "date": date(2020 + i // 12, i % 12 + 1, 1).isoformat(),
            "value": 4 + i / 100,
            "observation_id": str(i),
        }
        for i in range(n)
    ]


def test_outlook_preserves_calendar_and_lineage():
    data = series()
    data.pop(30)
    result = monthly_outlook(data, unit="percent")
    assert result["forecast"][0]["date"] == "2025-01-01"
    assert result["rolling_holdout_observations"] == 12
    assert "30" not in result["input_observation_ids"]
    assert all(
        0 <= p["scenario_low"] <= p["value"] <= p["scenario_high"] <= 100
        for p in result["forecast"]
    )


def test_unsupported_coverage_and_duplicates():
    assert monthly_outlook(series(20), unit="percent")["status"] == "unsupported"
    data = series()
    data.append(data[-1])
    assert monthly_outlook(data, unit="percent")["status"] == "unsupported"
    data = series()
    data[-1]["value"] = float("inf")
    assert monthly_outlook(data, unit="percent")["status"] == "unsupported"


def test_holdout_does_not_fit_future_values():
    result = monthly_outlook(series(), unit="percent")
    assert result["rolling_holdout_mae"]["persistence"] == pytest.approx(0.01)
    assert result["rolling_holdout_mae"]["damped_drift"] == pytest.approx(0, abs=1e-12)
    with pytest.raises(ValueError):
        monthly_outlook(series(), unit="percent", horizon=13)


def test_constant_and_null_series():
    data = series()
    for p in data:
        p["value"] = 200
    data[0]["value"] = None
    result = monthly_outlook(data, unit="jobs")
    assert result["method"] == "persistence"
    assert result["forecast"][0]["value"] == 200
