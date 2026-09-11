from __future__ import annotations

import calendar
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from mijobs.domain import ObservationInput
from mijobs.sources.base import FetchedArtifact, SourceConnector, SourceFetchError


class CensusConnector(SourceConnector):
    source_id = "us_census_qwi"
    base_url = "https://api.census.gov/data/timeseries/qwi"
    parser_version = "census-qwi/1"
    ALLOWED_ENDPOINTS = {"sa", "se", "rh"}

    def __init__(self, api_key: str | None, client: httpx.Client | None = None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=30.0)

    def healthcheck(self) -> bool:
        if not self.api_key:
            return False
        try:
            response = self.client.get(
                f"{self.base_url}/sa",
                params={"get": "Emp", "for": "state:26", "time": "latest", "key": self.api_key},
            )
            return response.is_success
        except httpx.HTTPError:
            return False

    def fetch_qwi(
        self,
        *,
        endpoint: str,
        indicators: list[str],
        geography: str,
        time: str,
        filters: dict[str, str] | None = None,
    ) -> FetchedArtifact:
        if endpoint not in self.ALLOWED_ENDPOINTS:
            raise ValueError(f"QWI endpoint must be one of {sorted(self.ALLOWED_ENDPOINTS)}")
        if not indicators:
            raise ValueError("at least one QWI indicator is required")
        if not self.api_key:
            raise SourceFetchError("CENSUS_API_KEY is required for current QWI API access")
        params: dict[str, str] = {
            "get": ",".join(indicators),
            "for": geography,
            "time": time,
            "key": self.api_key,
        }
        params.update(filters or {})
        url = f"{self.base_url}/{endpoint}"
        response = self.client.get(url, params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"Census QWI HTTP request failed: {exc}") from exc
        try:
            json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise SourceFetchError("Census QWI returned non-JSON content") from exc
        safe_params = {k: v for k, v in params.items() if k != "key"}
        return FetchedArtifact(
            source_id=self.source_id,
            locator=f"{url}?query={json.dumps(safe_params, sort_keys=True)}",
            retrieved_at=datetime.now(timezone.utc),
            content=response.content,
            media_type="application/json",
            parser_version=self.parser_version,
            metadata={"request": safe_params, "endpoint": endpoint},
        )

    @staticmethod
    def rows(artifact: FetchedArtifact) -> list[dict[str, str]]:
        body = json.loads(artifact.content)
        if not isinstance(body, list) or not body or not isinstance(body[0], list):
            raise SourceFetchError("unexpected Census tabular JSON structure")
        header = [str(column) for column in body[0]]
        rows: list[dict[str, str]] = []
        for row in body[1:]:
            if len(row) != len(header):
                raise SourceFetchError("Census row width does not match header")
            rows.append(dict(zip(header, map(str, row), strict=True)))
        return rows

    def normalize_qwi(
        self,
        artifact: FetchedArtifact,
        *,
        indicator_units: dict[str, str],
        geography_type: str,
        geography_fields: tuple[str, ...],
        taxonomy_system: str | None = None,
        taxonomy_version: str | None = None,
        taxonomy_field: str | None = None,
    ) -> list[ObservationInput]:
        """Normalize selected QWI indicators with explicit units and dimensions.

        QWI indicators have different semantics/units, so callers must provide a unit for
        every indicator being normalized rather than relying on implicit coercion.
        """
        if not indicator_units:
            raise ValueError("indicator_units must not be empty")
        rows = self.rows(artifact)
        observations: list[ObservationInput] = []
        for row in rows:
            missing_geo = [field for field in geography_fields if field not in row]
            if missing_geo:
                raise SourceFetchError(f"QWI row missing geography fields: {missing_geo}")
            geo_parts = [row[field] for field in geography_fields]
            geography_code = ":".join(geo_parts)
            period_start, period_end, period_basis = _qwi_period(row.get("time"))
            taxonomy_code = row.get(taxonomy_field) if taxonomy_field else None
            dimensions = {
                key: value
                for key, value in row.items()
                if key not in indicator_units and key not in {"time", *geography_fields}
            }
            dimension_key = ":".join(f"{key}={dimensions[key]}" for key in sorted(dimensions))
            for indicator, unit in indicator_units.items():
                if indicator not in row:
                    raise SourceFetchError(f"QWI row missing requested indicator: {indicator}")
                value_text = row[indicator]
                try:
                    numeric = Decimal(value_text.replace(",", ""))
                except InvalidOperation:
                    numeric = None
                key_parts = [
                    "qwi",
                    indicator,
                    row.get("time", "unknown"),
                    geography_type,
                    geography_code,
                ]
                if dimension_key:
                    key_parts.append(dimension_key)
                observations.append(
                    ObservationInput(
                        observation_key=":".join(key_parts),
                        metric=f"qwi.{indicator}",
                        value_text=value_text,
                        numeric_value=numeric,
                        unit=unit,
                        geography_type=geography_type,
                        geography_code=geography_code,
                        period_start=period_start,
                        period_end=period_end,
                        period_basis=period_basis,
                        taxonomy_system=taxonomy_system,
                        taxonomy_version=taxonomy_version,
                        taxonomy_code=taxonomy_code,
                        release_status="published",
                        metadata={"dimensions": dimensions, "indicator": indicator},
                    )
                )
        return observations


def _qwi_period(raw: str | None) -> tuple[date | None, date | None, str | None]:
    if raw is None:
        return None, None, None
    match = re.fullmatch(r"(\d{4})-Q([1-4])", raw)
    if not match:
        return None, None, raw
    year = int(match.group(1))
    quarter = int(match.group(2))
    start_month = 1 + (quarter - 1) * 3
    end_month = start_month + 2
    return (
        date(year, start_month, 1),
        date(year, end_month, calendar.monthrange(year, end_month)[1]),
        "quarterly",
    )
