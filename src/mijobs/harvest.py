"""Harvest orchestration: manifest-driven data collection from official sources.

Design principles:
- Manifest-driven: tasks are declarative data, not hardcoded logic.
- Runtime-validated: each task reports success/skip/error independently.
- Idempotent: re-running harvest reuses content-addressed artifacts.
- No silent imputation: missing data is reported as "skipped", never filled.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from mijobs.artifact_store import ArtifactStore
from mijobs.domain import ObservationInput
from mijobs.ingestion import Ingestor
from mijobs.sources.base import FetchedArtifact, SourceFetchError
from mijobs.sources.bls import BLSConnector
from mijobs.sources.census import CensusConnector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BLSHarvestTask:
    """A single BLS time-series harvest task."""

    series_ids: tuple[str, ...]
    start_year: int
    end_year: int
    geography_type: str = "national"
    geography_code: str | None = None
    geography_name: str | None = None
    metric_prefix: str = "bls"
    unit: str = "reported_value"
    label: str = ""

    def __post_init__(self) -> None:
        if not self.series_ids:
            raise ValueError("BLSHarvestTask requires at least one series ID")
        if len(self.series_ids) > 50:
            raise ValueError("BLSHarvestTask allows at most 50 series IDs per task")
        if self.start_year > self.end_year:
            raise ValueError("BLSHarvestTask: start_year must be <= end_year")
        if self.end_year - self.start_year + 1 > 20:
            raise ValueError("BLSHarvestTask: time range must not exceed 20 years")


@dataclass(frozen=True, slots=True)
class QWIHarvestTask:
    """A single Census QWI harvest task (one API call per quarter)."""

    endpoint: str
    indicators: tuple[str, ...]
    geography: str
    start_year: int
    end_year: int
    indicator_units: dict[str, str] = field(default_factory=dict)
    geography_type: str = "state"
    geography_fields: tuple[str, ...] = ("state",)
    label: str = ""

    def __post_init__(self) -> None:
        if self.endpoint not in {"sa", "se", "rh"}:
            raise ValueError(f"QWIHarvestTask: endpoint must be sa, se, or rh, got {self.endpoint!r}")
        if not self.indicators:
            raise ValueError("QWIHarvestTask requires at least one indicator")
        if self.start_year > self.end_year:
            raise ValueError("QWIHarvestTask: start_year must be <= end_year")

    def quarters(self) -> list[str]:
        """Generate all YYYY-Qn strings in the range (inclusive)."""
        result: list[str] = []
        for year in range(self.start_year, self.end_year + 1):
            for q in range(1, 5):
                result.append(f"{year}-Q{q}")
        return result


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Outcome of a single harvest task execution."""

    label: str
    status: str  # "ok" | "skipped" | "error"
    observations: int = 0
    locator: str | None = None
    error: str | None = None
    skipped_detail: str | None = None


@dataclass(frozen=True, slots=True)
class HarvestReport:
    """Aggregated results from a harvest run."""

    results: tuple[TaskResult, ...]
    started_at: str
    finished_at: str

    @property
    def total_observations(self) -> int:
        return sum(r.observations for r in self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.status == "ok")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "error")

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_observations": self.total_observations,
            "succeeded": self.succeeded,
            "skipped": self.skipped,
            "failed": self.failed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "results": [
                {
                    "label": r.label,
                    "status": r.status,
                    "observations": r.observations,
                    "locator": r.locator,
                    "error": r.error,
                    "skipped_detail": r.skipped_detail,
                }
                for r in self.results
            ],
        }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class HarvestRunner:
    """Executes a sequence of harvest tasks against live sources.

    Each task is independent: a failure in one does not abort the rest.
    The runner is idempotent — re-running with the same tasks will reuse
    content-addressed artifacts and skip duplicate observations.
    """

    def __init__(
        self,
        session: Session,
        store: ArtifactStore,
        *,
        bls: BLSConnector | None = None,
        census: CensusConnector | None = None,
        actor: str = "harvest",
    ) -> None:
        self.session = session
        self.store = store
        self.ingestor = Ingestor(session, store, actor=actor)
        self.bls = bls
        self.census = census

    def run_bls_task(self, task: BLSHarvestTask) -> TaskResult:
        """Execute a single BLS harvest task."""
        label = task.label or f"bls:{','.join(task.series_ids)}:{task.start_year}-{task.end_year}"
        if self.bls is None:
            return TaskResult(label=label, status="skipped", skipped_detail="BLS connector not configured")
        try:
            artifact = self.bls.fetch_series(
                list(task.series_ids),
                start_year=task.start_year,
                end_year=task.end_year,
            )
        except SourceFetchError as exc:
            logger.warning("BLS task %s failed: %s", label, exc)
            return TaskResult(label=label, status="error", error=str(exc))
        except ValueError as exc:
            return TaskResult(label=label, status="error", error=str(exc))

        # Check if the response contains actual data (BLS returns empty data
        # for series that don't exist in the requested range)
        try:
            body = json.loads(artifact.content)
            series_list = body.get("Results", {}).get("series", [])
            total_data_points = sum(len(s.get("data", [])) for s in series_list)
            if total_data_points == 0:
                return TaskResult(
                    label=label,
                    status="skipped",
                    skipped_detail="BLS returned no data points for requested series/range",
                    locator=artifact.locator,
                )
        except (ValueError, KeyError):
            pass  # Let normalizer handle structural issues

        def _normalizer(art: FetchedArtifact) -> list[ObservationInput]:
            return self.bls.normalize(  # type: ignore[union-attr]
                art,
                geography_type=task.geography_type,
                geography_code=task.geography_code,
                geography_name=task.geography_name,
                metric_prefix=task.metric_prefix,
                unit=task.unit,
            )

        try:
            _, observations = self.ingestor.ingest(artifact, normalizer=_normalizer)
        except Exception as exc:
            logger.warning("BLS ingest failed for %s: %s", label, exc)
            return TaskResult(label=label, status="error", error=f"ingest: {exc}", locator=artifact.locator)

        return TaskResult(
            label=label,
            status="ok",
            observations=len(observations),
            locator=artifact.locator,
        )

    def run_qwi_task(self, task: QWIHarvestTask) -> TaskResult:
        """Execute a QWI harvest task (one API call per quarter).

        Empty quarters are expected (QWI lags ~2 quarters) and reported as
        skipped rather than errors.
        """
        label = task.label or f"qwi:{task.endpoint}:{task.geography}:{task.start_year}-{task.end_year}"
        if self.census is None:
            return TaskResult(label=label, status="skipped", skipped_detail="Census connector not configured")

        quarters = task.quarters()
        total_obs = 0
        errors: list[str] = []
        empty_quarters = 0

        for q in quarters:
            try:
                artifact = self.census.fetch_qwi(
                    endpoint=task.endpoint,
                    indicators=list(task.indicators),
                    geography=task.geography,
                    time=q,
                )
            except SourceFetchError as exc:
                errors.append(f"{q}: {exc}")
                continue
            except ValueError as exc:
                errors.append(f"{q}: {exc}")
                continue

            # Check for empty response
            try:
                rows = CensusConnector.rows(artifact)
                if not rows:
                    empty_quarters += 1
                    continue
            except SourceFetchError:
                empty_quarters += 1
                continue

            def _normalizer(art: FetchedArtifact) -> list[ObservationInput]:
                return self.census.normalize_qwi(  # type: ignore[union-attr]
                    art,
                    indicator_units=task.indicator_units,
                    geography_type=task.geography_type,
                    geography_fields=task.geography_fields,
                )

            try:
                _, observations = self.ingestor.ingest(artifact, normalizer=_normalizer)
                total_obs += len(observations)
            except Exception as exc:
                errors.append(f"{q} ingest: {exc}")

        if total_obs == 0 and not errors:
            detail = f"All {len(quarters)} quarters returned empty (expected if QWI lags)"
            if empty_quarters > 0:
                detail += f" [{empty_quarters} empty]"
            return TaskResult(label=label, status="skipped", skipped_detail=detail)

        if total_obs == 0 and errors:
            return TaskResult(
                label=label,
                status="error",
                error=f"All quarters failed: {'; '.join(errors[:3])}",
            )

        status = "ok"  # partial success still counts as ok
        if errors:
            logger.warning("QWI task %s: %d quarter(s) had errors: %s", label, len(errors), errors[:3])

        return TaskResult(
            label=label,
            status=status,
            observations=total_obs,
            locator=f"qwi:{task.endpoint}:{task.geography}:{quarters[0]}..{quarters[-1]}",
        )

    def run(self, tasks: list[tuple[str, Any]]) -> HarvestReport:
        """Execute a list of (kind, task) pairs and return a report.

        Args:
            tasks: List of tuples where first element is "bls" or "qwi"
                   and second is the corresponding task dataclass.
        """
        from datetime import UTC, datetime

        started = datetime.now(UTC).isoformat()
        results: list[TaskResult] = []

        for kind, task in tasks:
            if kind == "bls":
                results.append(self.run_bls_task(task))
            elif kind == "qwi":
                results.append(self.run_qwi_task(task))
            else:
                results.append(
                    TaskResult(
                        label=f"unknown:{kind}",
                        status="error",
                        error=f"Unknown task kind: {kind!r}",
                    )
                )

        finished = datetime.now(UTC).isoformat()
        return HarvestReport(results=tuple(results), started_at=started, finished_at=finished)


# ---------------------------------------------------------------------------
# Default plan builder
# ---------------------------------------------------------------------------


def default_plan(
    *,
    start_year: int = 2020,
    end_year: int = 2026,
    include_qwi: bool = True,
) -> list[tuple[str, Any]]:
    """Build the default harvest plan with verified series.

    BLS national CPS series (verified live through Aug 2026):
    - LNS14000000: Seasonally-adjusted unemployment rate
    - LNS13000000: Seasonally-adjusted unemployed persons (thousands)
    - LNS11000000: Seasonally-adjusted labor force (thousands)
    - LNS12000000: Seasonally-adjusted civilian employment (thousands)

    Census QWI (state:26 = Michigan):
    - Emp: Total employment (quarterly)
    """
    tasks: list[tuple[str, Any]] = []

    # BLS national series — split into 20-year chunks if needed
    bls_series = (
        "LNS14000000",  # SA unemployment rate (%)
        "LNS13000000",  # SA unemployed (thousands)
        "LNS11000000",  # SA labor force (thousands)
        "LNS12000000",  # SA civilian employment (thousands)
    )
    # BLS v2 max range is 20 years; 2020-2026 is 7 years, fits in one request
    tasks.append(
        (
            "bls",
            BLSHarvestTask(
                series_ids=bls_series,
                start_year=start_year,
                end_year=end_year,
                geography_type="national",
                geography_code="US",
                geography_name="United States",
                metric_prefix="bls.cps",
                unit="reported_value",
                label=f"bls.cps.national:{start_year}-{end_year}",
            ),
        )
    )

    if include_qwi:
        # QWI lags ~2 quarters; use end_year-1 to avoid guaranteed-empty trailing quarters
        qwi_end = min(end_year, date.today().year - 1)
        tasks.append(
            (
                "qwi",
                QWIHarvestTask(
                    endpoint="sa",
                    indicators=("Emp",),
                    geography="state:26",
                    start_year=start_year,
                    end_year=qwi_end,
                    indicator_units={"Emp": "persons"},
                    geography_type="state",
                    geography_fields=("state",),
                    label=f"qwi.sa.state:26:{start_year}-{qwi_end}",
                ),
            )
        )

    return tasks
