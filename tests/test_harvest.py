"""Tests for the harvest orchestration module."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from mijobs.artifact_store import ArtifactStore
from mijobs.domain import ObservationInput
from mijobs.harvest import (
    BLSHarvestTask,
    HarvestReport,
    HarvestRunner,
    QWIHarvestTask,
    TaskResult,
    default_plan,
)
from mijobs.sources.base import FetchedArtifact, SourceFetchError


@pytest.fixture
def tmp_store(tmp_path):
    return ArtifactStore(tmp_path / "artifacts")


class TestBLSHarvestTask:
    def test_valid_task(self) -> None:
        task = BLSHarvestTask(
            series_ids=("LNS14000000",),
            start_year=2020,
            end_year=2026,
        )
        assert task.series_ids == ("LNS14000000",)
        assert task.start_year == 2020
        assert task.end_year == 2026

    def test_empty_series_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one series"):
            BLSHarvestTask(series_ids=(), start_year=2020, end_year=2026)

    def test_too_many_series_raises(self) -> None:
        with pytest.raises(ValueError, match="at most 50"):
            BLSHarvestTask(
                series_ids=tuple(f"S{i:010d}" for i in range(51)),
                start_year=2020,
                end_year=2026,
            )

    def test_invalid_year_range_raises(self) -> None:
        with pytest.raises(ValueError, match="start_year must be"):
            BLSHarvestTask(
                series_ids=("S1",),
                start_year=2026,
                end_year=2020,
            )

    def test_range_exceeds_20_years_raises(self) -> None:
        with pytest.raises(ValueError, match="20 years"):
            BLSHarvestTask(
                series_ids=("S1",),
                start_year=2000,
                end_year=2026,
            )


class TestQWIHarvestTask:
    def test_valid_task(self) -> None:
        task = QWIHarvestTask(
            endpoint="sa",
            indicators=("Emp",),
            geography="state:26",
            start_year=2020,
            end_year=2022,
            indicator_units={"Emp": "persons"},
        )
        quarters = task.quarters()
        assert quarters[0] == "2020-Q1"
        assert quarters[-1] == "2022-Q4"
        assert len(quarters) == 12

    def test_invalid_endpoint_raises(self) -> None:
        with pytest.raises(ValueError, match="endpoint must be"):
            QWIHarvestTask(
                endpoint="invalid",
                indicators=("Emp",),
                geography="state:26",
                start_year=2020,
                end_year=2022,
            )

    def test_no_indicators_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one indicator"):
            QWIHarvestTask(
                endpoint="sa",
                indicators=(),
                geography="state:26",
                start_year=2020,
                end_year=2022,
            )


class TestDefaultPlan:
    def test_returns_tasks(self) -> None:
        tasks = default_plan(start_year=2020, end_year=2026)
        assert len(tasks) == 2
        assert tasks[0][0] == "bls"
        assert tasks[1][0] == "qwi"

    def test_exclude_qwi(self) -> None:
        tasks = default_plan(start_year=2020, end_year=2026, include_qwi=False)
        assert len(tasks) == 1
        assert tasks[0][0] == "bls"

    def test_bls_task_has_verified_series(self) -> None:
        tasks = default_plan(start_year=2020, end_year=2026)
        bls_task = tasks[0][1]
        assert "LNS14000000" in bls_task.series_ids
        assert "LNS11000000" in bls_task.series_ids
        assert "LNS12000000" in bls_task.series_ids
        assert "LNS13000000" in bls_task.series_ids


class TestHarvestRunner:
    def test_run_bls_no_connector(self, tmp_store, db_session) -> None:
        runner = HarvestRunner(db_session, tmp_store, bls=None)
        task = BLSHarvestTask(
            series_ids=("LNS14000000",),
            start_year=2020,
            end_year=2026,
            label="test",
        )
        result = runner.run_bls_task(task)
        assert result.status == "skipped"
        assert "not configured" in (result.skipped_detail or "")

    def test_run_qwi_no_connector(self, tmp_store, db_session) -> None:
        runner = HarvestRunner(db_session, tmp_store, census=None)
        task = QWIHarvestTask(
            endpoint="sa",
            indicators=("Emp",),
            geography="state:26",
            start_year=2020,
            end_year=2020,
            indicator_units={"Emp": "persons"},
            label="test",
        )
        result = runner.run_qwi_task(task)
        assert result.status == "skipped"
        assert "not configured" in (result.skipped_detail or "")

    def test_run_bls_success(self, tmp_store, db_session) -> None:
        mock_bls = MagicMock()
        artifact = FetchedArtifact(
            source_id="us_bls_api",
            locator="test-locator",
            retrieved_at=datetime.now(UTC),
            content=json.dumps(
                {
                    "status": "REQUEST_SUCCEEDED",
                    "Results": {
                        "series": [
                            {
                                "seriesID": "LNS14000000",
                                "catalog": {},
                                "data": [
                                    {"year": "2026", "period": "M08", "value": "4.1", "footnotes": []}
                                ],
                            }
                        ]
                    },
                }
            ).encode(),
            media_type="application/json",
            parser_version="bls-v2/1",
        )
        mock_bls.fetch_series.return_value = artifact
        mock_bls.normalize.return_value = [
            ObservationInput(
                observation_key="bls:LNS14000000:2026:M08",
                metric="bls.cps.LNS14000000",
                value_text="4.1",
                unit="percent",
                numeric_value=Decimal("4.1"),
                geography_type="national",
                geography_code="US",
                period_start=date(2026, 8, 1),
                period_end=date(2026, 8, 31),
                period_basis="monthly",
            )
        ]

        runner = HarvestRunner(db_session, tmp_store, bls=mock_bls)
        task = BLSHarvestTask(
            series_ids=("LNS14000000",),
            start_year=2020,
            end_year=2026,
            label="test-bls",
        )
        result = runner.run_bls_task(task)
        assert result.status == "ok"
        assert result.observations == 1

    def test_run_bls_fetch_error(self, tmp_store, db_session) -> None:
        mock_bls = MagicMock()
        mock_bls.fetch_series.side_effect = SourceFetchError("BLS request failed: rate limit")
        runner = HarvestRunner(db_session, tmp_store, bls=mock_bls)
        task = BLSHarvestTask(
            series_ids=("LNS14000000",),
            start_year=2020,
            end_year=2026,
            label="test-err",
        )
        result = runner.run_bls_task(task)
        assert result.status == "error"
        assert "rate limit" in (result.error or "")

    def test_run_qwi_all_empty(self, tmp_store, db_session) -> None:
        mock_census = MagicMock()
        mock_census.fetch_qwi.return_value = FetchedArtifact(
            source_id="us_census_qwi",
            locator="qwi-test",
            retrieved_at=datetime.now(UTC),
            content=b"[]",
            media_type="application/json",
            parser_version="census-qwi/1",
        )
        # rows() will raise SourceFetchError on empty list
        runner = HarvestRunner(db_session, tmp_store, census=mock_census)
        task = QWIHarvestTask(
            endpoint="sa",
            indicators=("Emp",),
            geography="state:26",
            start_year=2020,
            end_year=2020,
            indicator_units={"Emp": "persons"},
            label="test-qwi-empty",
        )
        result = runner.run_qwi_task(task)
        assert result.status == "skipped"
        assert "empty" in (result.skipped_detail or "").lower()

    def test_run_unknown_kind(self, tmp_store, db_session) -> None:
        runner = HarvestRunner(db_session, tmp_store)
        report = runner.run([("unknown", None)])
        assert report.failed == 1
        assert "Unknown task kind" in report.results[0].error or ""


class TestHarvestReport:
    def test_to_dict(self) -> None:
        report = HarvestReport(
            results=(
                TaskResult(label="a", status="ok", observations=10),
                TaskResult(label="b", status="skipped", skipped_detail="no data"),
                TaskResult(label="c", status="error", error="failed"),
            ),
            started_at="2026-01-01T00:00:00Z",
            finished_at="2026-01-01T00:01:00Z",
        )
        d = report.to_dict()
        assert d["total_observations"] == 10
        assert d["succeeded"] == 1
        assert d["skipped"] == 1
        assert d["failed"] == 1
        assert len(d["results"]) == 3
