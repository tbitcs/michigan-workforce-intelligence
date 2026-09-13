from __future__ import annotations

import calendar
import json
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from mijobs.domain import ObservationInput
from mijobs.sources.base import FetchedArtifact, SourceConnector, SourceFetchError


class BLSConnector(SourceConnector):
    source_id = "us_bls_api"
    api_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    parser_version = "bls-v2/1"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=30.0)

    def healthcheck(self) -> bool:
        try:
            response = self.client.get(f"{self.api_url}LNS14000000?latest=true")
            return response.is_success
        except httpx.HTTPError:
            return False

    def fetch_series(
        self,
        series_ids: list[str],
        *,
        start_year: int,
        end_year: int,
        catalog: bool = True,
    ) -> FetchedArtifact:
        if not series_ids or len(series_ids) > 50:
            raise ValueError("BLS request requires 1-50 series IDs")
        if start_year > end_year or start_year < 1900 or end_year > 2200:
            raise ValueError("invalid year range")
        if end_year - start_year > 20:
            raise ValueError("BLS v2 time range must not exceed 20 years")
        payload: dict[str, Any] = {
            "seriesid": series_ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
            "catalog": catalog,
        }
        if self.api_key:
            payload["registrationkey"] = self.api_key
        response = self.client.post(self.api_url, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"BLS HTTP request failed: {exc}") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise SourceFetchError("BLS returned non-JSON content") from exc
        if body.get("status") != "REQUEST_SUCCEEDED":
            raise SourceFetchError(f"BLS request failed: {body.get('message', body.get('status'))}")
        locator = f"{self.api_url}#series={','.join(series_ids)}&{start_year}-{end_year}"
        return FetchedArtifact(
            source_id=self.source_id,
            locator=locator,
            retrieved_at=datetime.now(UTC),
            content=response.content,
            media_type="application/json",
            parser_version=self.parser_version,
            metadata={"request": {k: v for k, v in payload.items() if k != "registrationkey"}},
        )

    def normalize(
        self,
        artifact: FetchedArtifact,
        *,
        geography_type: str | None = None,
        geography_code: str | None = None,
        geography_name: str | None = None,
        metric_prefix: str = "bls",
        unit: str = "reported_value",
    ) -> list[ObservationInput]:
        try:
            body = json.loads(artifact.content)
            series = body["Results"]["series"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise SourceFetchError("invalid BLS payload structure") from exc
        observations: list[ObservationInput] = []
        for item in series:
            series_id = str(item["seriesID"])
            catalog = item.get("catalog", {})
            for point in item.get("data", []):
                period = str(point.get("period", ""))
                if period == "M13":
                    period_basis = "annual_average"
                    period_start = date(int(point["year"]), 1, 1)
                    period_end = date(int(point["year"]), 12, 31)
                elif period.startswith("M") and period[1:].isdigit() and 1 <= int(period[1:]) <= 12:
                    month = int(period[1:])
                    period_basis = "monthly"
                    period_start = date(int(point["year"]), month, 1)
                    year = int(point["year"])
                    period_end = date(year, month, calendar.monthrange(year, month)[1])
                else:
                    period_basis = period or "unknown"
                    period_start = date(int(point["year"]), 1, 1)
                    period_end = None
                value_text = str(point.get("value", ""))
                try:
                    numeric = Decimal(value_text.replace(",", ""))
                except InvalidOperation:
                    numeric = None
                footnotes = [f for f in point.get("footnotes", []) if f]
                observation_key = f"bls:{series_id}:{point['year']}:{period}"
                observations.append(
                    ObservationInput(
                        observation_key=observation_key,
                        metric=f"{metric_prefix}.{series_id}",
                        value_text=value_text,
                        numeric_value=numeric,
                        unit=unit,
                        geography_type=geography_type,
                        geography_code=geography_code,
                        geography_name=geography_name,
                        period_start=period_start,
                        period_end=period_end,
                        period_basis=period_basis,
                        release_status="preliminary"
                        if any(f.get("code") == "P" for f in footnotes)
                        else "published",
                        uncertainty={"footnotes": footnotes},
                        metadata={"series_id": series_id, "catalog": catalog, "period_name": point.get("periodName")},
                    )
                )
        return observations
