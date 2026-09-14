"""Bounded read-only regional trend context with observation lineage."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from mijobs.models import Observation
from mijobs.outlook import monthly_outlook


def economic_series(
    session: Session, *, geography_code: str, metric: str, limit: int = 120
) -> dict[str, Any]:
    if not geography_code or not metric or not 1 <= limit <= 500:
        raise ValueError("Exact geography/metric and limit 1-500 are required")
    newer = aliased(Observation)
    query = (
        select(Observation)
        .where(
            Observation.geography_code == geography_code,
            or_(
                Observation.metric == metric,
                Observation.metadata_json["indicator"].as_string() == metric,
            ),
            ~select(newer.id)
            .where(
                newer.observation_key == Observation.observation_key,
                newer.version > Observation.version,
            )
            .exists(),
        )
        .order_by(Observation.period_start.desc().nullslast(), Observation.created_at.desc())
        .limit(limit + 1)
    )
    rows = list(session.scalars(query))
    outlook = {"status": "unsupported", "reason": "Monthly compatible series required"}
    selected = rows[:limit]
    if (
        selected
        and all(o.period_basis == "monthly" for o in selected)
        and len({(o.unit, o.adjustment, o.metric) for o in selected}) == 1
    ):
        outlook = monthly_outlook(
            [
                {"date": str(o.period_start), "value": o.numeric_value, "observation_id": o.id}
                for o in selected
            ],
            unit=selected[0].unit,
        )
    return {
        "outlook": outlook,
        "geography_code": geography_code,
        "metric": metric,
        "status": "available" if rows else "missing",
        "truncated": len(rows) > limit,
        "points": [
            {
                "observation_id": o.id,
                "artifact_id": o.source_artifact_id,
                "value": o.numeric_value,
                "unit": o.unit,
                "period_start": str(o.period_start) if o.period_start else None,
                "period_end": str(o.period_end) if o.period_end else None,
                "period_basis": o.period_basis,
                "adjustment": o.adjustment,
                "reference_year": o.metadata_json.get("year"),
                "margin_of_error": o.metadata_json.get("margin_of_error"),
            }
            for o in rows[:limit]
        ],
        "limitations": [
            "Do not mix seasonal adjustments, units or periods.",
            "Missing values are not zero; reference outlooks are statistical scenarios, not causal layoff predictions.",
        ],
    }


def economic_coverage(session: Session, geography_code: str | None = None) -> dict[str, Any]:
    query = select(Observation.metric, Observation.geography_code).distinct()
    if geography_code:
        query = query.where(Observation.geography_code == geography_code)
    rows = session.execute(
        query.order_by(Observation.metric, Observation.geography_code).limit(1001)
    ).all()
    return {
        "truncated": len(rows) > 1000,
        "available": [{"metric": metric, "geography_code": geo} for metric, geo in rows[:1000]],
        "target_geographies": {
            "26099": "Macomb County",
            "26125": "Oakland County",
            "26163": "Wayne County",
            "26": "Michigan",
        },
        "notes": "Availability means stored observations, not complete/current coverage. Query exact series for periods and provenance.",
    }
