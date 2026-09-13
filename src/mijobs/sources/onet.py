from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

import httpx

from mijobs.domain import ObservationInput
from mijobs.sources.base import FetchedArtifact, SourceConnector, SourceFetchError


class ONetConnector(SourceConnector):
    """O*NET 31.x public bulk JSON connector for occupation capability profiles."""

    source_id = "us_onet"
    base_url = "https://www.onetcenter.org/dl_files/database"
    parser_version = "onet-json-ratings/1"
    TAXONOMY_VERSION = "2019"
    ALLOWED_RATING_DATASETS: ClassVar[set[str]] = {
        "essential_skills",
        "transferable_skills",
        "abilities",
        "knowledge",
        "work_activities",
    }
    ALLOWED_CATEGORICAL_DATASETS: ClassVar[set[str]] = {"software_skills"}
    ALLOWED_DATASETS = ALLOWED_RATING_DATASETS | ALLOWED_CATEGORICAL_DATASETS

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=120.0, follow_redirects=True)

    def healthcheck(self) -> bool:
        try:
            response = self.client.head("https://www.onetcenter.org/database.html")
            return response.is_success
        except httpx.HTTPError:
            return False

    def fetch_rating_dataset(self, dataset: str, *, release: str = "31.0") -> FetchedArtifact:
        if dataset not in self.ALLOWED_DATASETS:
            raise ValueError(f"unsupported O*NET dataset: {dataset}")
        release_path = release.replace(".", "_")
        url = f"{self.base_url}/db_{release_path}_json/{dataset}.json"
        response = self.client.get(url)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"O*NET download failed: {exc}") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise SourceFetchError("O*NET returned non-JSON content") from exc
        if not isinstance(body, list):
            raise SourceFetchError("O*NET rating dataset must be a JSON array")
        return FetchedArtifact(
            source_id=self.source_id,
            locator=str(response.url),
            retrieved_at=datetime.now(UTC),
            content=response.content,
            media_type="application/json",
            dataset_version=release,
            parser_version=self.parser_version,
            metadata={
                "dataset": dataset,
                "database_release": release,
                "taxonomy_system": "O*NET-SOC",
                "taxonomy_version": self.TAXONOMY_VERSION,
                "soc_alignment": "2018",
            },
        )

    def normalize_ratings(self, artifact: FetchedArtifact) -> list[ObservationInput]:
        dataset = str(artifact.metadata.get("dataset", ""))
        if dataset not in self.ALLOWED_RATING_DATASETS:
            raise SourceFetchError("artifact metadata does not identify a supported O*NET rating dataset")
        release = artifact.dataset_version
        if not release:
            raise SourceFetchError("O*NET release version is required")
        try:
            rows: list[dict[str, Any]] = json.loads(artifact.content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise SourceFetchError("invalid O*NET JSON") from exc
        if not isinstance(rows, list):
            raise SourceFetchError("O*NET rating dataset must be a JSON array")

        observations: list[ObservationInput] = []
        required = {"onetsoc_code", "element_id", "element_name", "scale_id", "data_value"}
        for row in rows:
            if not isinstance(row, dict) or not required.issubset(row):
                raise SourceFetchError(f"O*NET {dataset} row missing required fields")
            value_text = str(row["data_value"])
            try:
                numeric = Decimal(value_text)
            except InvalidOperation:
                numeric = None
            suppressed = str(row.get("recommend_suppress", "N")).upper() == "Y"
            not_relevant = str(row.get("not_relevant", "N")).upper() == "Y"
            if suppressed:
                release_status = "suppression_recommended"
            elif not_relevant:
                release_status = "not_relevant"
            else:
                release_status = "published"
            onetsoc = str(row["onetsoc_code"])
            element_id = str(row["element_id"])
            scale_id = str(row["scale_id"])
            observations.append(
                ObservationInput(
                    observation_key=f"onet:{release}:{dataset}:{onetsoc}:{element_id}:{scale_id}",
                    metric=f"onet.{dataset}.{element_id}.{scale_id}",
                    value_text=value_text,
                    numeric_value=numeric,
                    unit="onet_rating",
                    period_basis="release_snapshot",
                    taxonomy_system="O*NET-SOC",
                    taxonomy_version=str(
                        artifact.metadata.get("taxonomy_version", self.TAXONOMY_VERSION)
                    ),
                    taxonomy_code=onetsoc,
                    release_status=release_status,
                    uncertainty={
                        "n": row.get("n"),
                        "standard_error": row.get("standard_error"),
                        "lower_ci_bound": row.get("lower_ci_bound"),
                        "upper_ci_bound": row.get("upper_ci_bound"),
                        "recommend_suppress": row.get("recommend_suppress"),
                    },
                    metadata={
                        "occupation_title": row.get("title"),
                        "element_id": element_id,
                        "element_name": row["element_name"],
                        "scale_id": scale_id,
                        "scale_name": row.get("scale_name"),
                        "not_relevant": row.get("not_relevant"),
                        "date_updated": row.get("date_updated") or row.get("date"),
                        "domain_source": row.get("domain_source"),
                        "dataset": dataset,
                        "database_release": release,
                        "soc_alignment": artifact.metadata.get("soc_alignment", "2018"),
                    },
                )
            )
        return observations

    def normalize_software_skills(self, artifact: FetchedArtifact) -> list[ObservationInput]:
        """Normalize occupation-linked software examples without inventing numeric ratings."""
        if artifact.metadata.get("dataset") != "software_skills":
            raise SourceFetchError("artifact metadata does not identify software_skills")
        release = artifact.dataset_version
        if not release:
            raise SourceFetchError("O*NET database release version is required")
        try:
            rows: list[dict[str, Any]] = json.loads(artifact.content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise SourceFetchError("invalid O*NET software skills JSON") from exc
        if not isinstance(rows, list):
            raise SourceFetchError("O*NET software skills dataset must be a JSON array")
        required = {"onetsoc_code", "workplace_example", "element_id", "element_name"}
        observations: list[ObservationInput] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not required.issubset(row):
                raise SourceFetchError("O*NET software skills row missing required fields")
            onetsoc = str(row["onetsoc_code"])
            example = str(row["workplace_example"])
            element_id = str(row["element_id"])
            observations.append(
                ObservationInput(
                    observation_key=(
                        f"onet:{release}:software_skills:{onetsoc}:{element_id}:{index}:"
                        f"{example.casefold()}"
                    ),
                    metric="onet.software_skill.example",
                    value_text=example,
                    unit="software_example",
                    period_basis="release_snapshot",
                    taxonomy_system="O*NET-SOC",
                    taxonomy_version=str(
                        artifact.metadata.get("taxonomy_version", self.TAXONOMY_VERSION)
                    ),
                    taxonomy_code=onetsoc,
                    release_status="published",
                    metadata={
                        "occupation_title": row.get("title"),
                        "element_id": element_id,
                        "element_name": row["element_name"],
                        "hot_technology": row.get("hot_technology"),
                        "in_demand": row.get("in_demand"),
                        "database_release": release,
                        "soc_alignment": artifact.metadata.get("soc_alignment", "2018"),
                    },
                )
            )
        return observations
