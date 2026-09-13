from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from mijobs.domain import ObservationInput
from mijobs.sources.base import FetchedArtifact, SourceConnector, SourceFetchError


class IPEDSConnector(SourceConnector):
    """NCES IPEDS bulk-file connector and deterministic normalizers.

    IPEDS publishes component files as ZIP archives containing CSV data. This adapter
    deliberately keeps collection year, release status, and taxonomy vintage explicit;
    those values must not be inferred later from a filename alone.
    """

    source_id = "us_nces_ipeds"
    base_url = "https://nces.ed.gov/ipeds/datacenter/data"
    parser_version = "ipeds-bulk/1"
    _SAFE_FILE = re.compile(r"^[A-Za-z0-9_\-]+\.zip$")

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=120.0, follow_redirects=True)

    def healthcheck(self) -> bool:
        try:
            response = self.client.head("https://nces.ed.gov/ipeds/use-the-data")
            return response.is_success
        except httpx.HTTPError:
            return False

    def fetch_data_file(
        self,
        filename: str,
        *,
        collection_year: int,
        release_status: str,
    ) -> FetchedArtifact:
        if not self._SAFE_FILE.fullmatch(filename):
            raise ValueError("IPEDS filename must be a simple .zip data-file name")
        if release_status not in {"provisional", "final"}:
            raise ValueError("IPEDS release_status must be 'provisional' or 'final'")
        url = f"{self.base_url}/{filename}"
        response = self.client.get(url)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"IPEDS bulk download failed: {exc}") from exc
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                if not any(name.lower().endswith(".csv") for name in archive.namelist()):
                    raise SourceFetchError("IPEDS ZIP contains no CSV member")
        except zipfile.BadZipFile as exc:
            raise SourceFetchError("IPEDS response is not a valid ZIP archive") from exc
        return FetchedArtifact(
            source_id=self.source_id,
            locator=str(response.url),
            retrieved_at=datetime.now(UTC),
            content=response.content,
            media_type="application/zip",
            dataset_version=str(collection_year),
            parser_version=self.parser_version,
            metadata={
                "filename": filename,
                "collection_year": collection_year,
                "release_status": release_status,
            },
        )

    def normalize_completions(
        self,
        artifact: FetchedArtifact,
        *,
        collection_year: int,
        cip_version: str,
        allowed_unitids: set[str] | None = None,
        allowed_award_levels: set[str] | None = None,
        unitid_field: str = "UNITID",
        cip_field: str = "CIPCODE",
        award_level_field: str = "AWLEVEL",
        total_field: str = "CTOTALT",
    ) -> list[ObservationInput]:
        """Normalize IPEDS Completions A rows to credential-award observations.

        Modern C*_A files include total awards by institution, 6-digit CIP and award
        level. Race/ethnicity/gender columns are intentionally retained only as source
        metadata in this baseline; the total is the canonical pipeline measure.
        """
        release_status = _release_status(artifact)
        rows = _csv_rows(artifact)
        required = {unitid_field, cip_field, award_level_field, total_field}
        _require_fields(rows, required, "IPEDS completions")
        period_start, period_end = _academic_year(collection_year)
        observations: list[ObservationInput] = []
        for row in rows:
            unitid = row[unitid_field].strip()
            cip = row[cip_field].strip()
            award_level = row[award_level_field].strip()
            if allowed_unitids is not None and unitid not in allowed_unitids:
                continue
            if allowed_award_levels is not None and award_level not in allowed_award_levels:
                continue
            value_text = row[total_field].strip()
            numeric = _decimal_or_none(value_text)
            observations.append(
                ObservationInput(
                    observation_key=(
                        f"ipeds:{collection_year}:completions:{unitid}:{cip}:{award_level}"
                    ),
                    metric="ipeds.completions.awards",
                    value_text=value_text,
                    numeric_value=numeric,
                    unit="awards",
                    geography_type="institution",
                    geography_code=unitid,
                    period_start=period_start,
                    period_end=period_end,
                    period_basis="academic_year",
                    taxonomy_system="CIP",
                    taxonomy_version=cip_version,
                    taxonomy_code=cip,
                    release_status=release_status,
                    metadata={
                        "component": "Completions",
                        "survey_file": artifact.metadata.get("filename"),
                        "collection_year": collection_year,
                        "award_level": award_level,
                        "award_level_field": award_level_field,
                        "total_field": total_field,
                    },
                )
            )
        return observations

    def normalize_12month_enrollment(
        self,
        artifact: FetchedArtifact,
        *,
        collection_year: int,
        allowed_unitids: set[str] | None = None,
        allowed_level_codes: set[str] | None = None,
        unitid_field: str = "UNITID",
        level_field: str = "EFFYLEV",
        total_field: str = "EFYTOTLT",
    ) -> list[ObservationInput]:
        """Normalize 12-month unduplicated enrollment by institution and level."""
        release_status = _release_status(artifact)
        rows = _csv_rows(artifact)
        required = {unitid_field, level_field, total_field}
        _require_fields(rows, required, "IPEDS 12-month enrollment")
        period_start, period_end = _academic_year(collection_year)
        observations: list[ObservationInput] = []
        for row in rows:
            unitid = row[unitid_field].strip()
            level = row[level_field].strip()
            if allowed_unitids is not None and unitid not in allowed_unitids:
                continue
            if allowed_level_codes is not None and level not in allowed_level_codes:
                continue
            value_text = row[total_field].strip()
            observations.append(
                ObservationInput(
                    observation_key=f"ipeds:{collection_year}:12m_enrollment:{unitid}:{level}",
                    metric="ipeds.enrollment.12_month_unduplicated",
                    value_text=value_text,
                    numeric_value=_decimal_or_none(value_text),
                    unit="students",
                    geography_type="institution",
                    geography_code=unitid,
                    period_start=period_start,
                    period_end=period_end,
                    period_basis="12_month",
                    release_status=release_status,
                    metadata={
                        "component": "12-month Enrollment",
                        "survey_file": artifact.metadata.get("filename"),
                        "collection_year": collection_year,
                        "level_code": level,
                        "level_field": level_field,
                        "total_field": total_field,
                        "unduplicated_headcount": True,
                    },
                )
            )
        return observations

    def normalize_fall_enrollment(
        self,
        artifact: FetchedArtifact,
        *,
        collection_year: int,
        allowed_unitids: set[str] | None = None,
        allowed_level_codes: set[str] | None = None,
        unitid_field: str = "UNITID",
        level_field: str = "EFALEVEL",
        total_field: str = "EFTOTLT",
    ) -> list[ObservationInput]:
        """Normalize Fall Enrollment A rows without inventing a universal snapshot date."""
        release_status = _release_status(artifact)
        rows = _csv_rows(artifact)
        required = {unitid_field, level_field, total_field}
        _require_fields(rows, required, "IPEDS fall enrollment")
        observations: list[ObservationInput] = []
        for row in rows:
            unitid = row[unitid_field].strip()
            level = row[level_field].strip()
            if allowed_unitids is not None and unitid not in allowed_unitids:
                continue
            if allowed_level_codes is not None and level not in allowed_level_codes:
                continue
            value_text = row[total_field].strip()
            observations.append(
                ObservationInput(
                    observation_key=f"ipeds:{collection_year}:fall_enrollment:{unitid}:{level}",
                    metric="ipeds.enrollment.fall",
                    value_text=value_text,
                    numeric_value=_decimal_or_none(value_text),
                    unit="students",
                    geography_type="institution",
                    geography_code=unitid,
                    period_basis=f"fall_{collection_year}",
                    release_status=release_status,
                    metadata={
                        "component": "Fall Enrollment",
                        "survey_file": artifact.metadata.get("filename"),
                        "collection_year": collection_year,
                        "level_code": level,
                        "level_field": level_field,
                        "total_field": total_field,
                        "note": "Institution reporting date/October 15 convention; no fabricated exact date stored.",
                    },
                )
            )
        return observations

    def normalize_institutions(
        self,
        artifact: FetchedArtifact,
        *,
        collection_year: int,
        state_filter: str | None = None,
        unitid_field: str = "UNITID",
        name_field: str = "INSTNM",
        state_field: str = "STABBR",
    ) -> list[ObservationInput]:
        """Normalize IPEDS institutional directory records for joinable UnitID context."""
        release_status = _release_status(artifact)
        rows = _csv_rows(artifact)
        _require_fields(rows, {unitid_field, name_field, state_field}, "IPEDS directory")
        observations: list[ObservationInput] = []
        for row in rows:
            state = row[state_field].strip()
            if state_filter is not None and state != state_filter:
                continue
            unitid = row[unitid_field].strip()
            name = row[name_field].strip()
            metadata_fields = (
                "CITY",
                "ZIP",
                "COUNTYCD",
                "COUNTYNM",
                "CONTROL",
                "SECTOR",
                "ICLEVEL",
                "LONGITUD",
                "LATITUDE",
            )
            metadata: dict[str, Any] = {key.lower(): row[key] for key in metadata_fields if key in row}
            metadata.update(
                {
                    "component": "Institutional Characteristics/Directory",
                    "survey_file": artifact.metadata.get("filename"),
                    "collection_year": collection_year,
                    "state": state,
                }
            )
            observations.append(
                ObservationInput(
                    observation_key=f"ipeds:{collection_year}:institution:{unitid}",
                    metric="ipeds.institution.active_record",
                    value_text="1",
                    numeric_value=Decimal(1),
                    unit="institution_record",
                    geography_type="institution",
                    geography_code=unitid,
                    geography_name=name,
                    period_basis=f"directory_{collection_year}",
                    release_status=release_status,
                    metadata=metadata,
                )
            )
        return observations


def _release_status(artifact: FetchedArtifact) -> str:
    status = str(artifact.metadata.get("release_status", "")).lower()
    if status not in {"provisional", "final"}:
        raise SourceFetchError("IPEDS artifact requires provisional/final release_status metadata")
    return status


def _academic_year(collection_year: int) -> tuple[date, date]:
    if collection_year < 1900 or collection_year > 2200:
        raise ValueError("collection_year is outside supported range")
    return date(collection_year - 1, 7, 1), date(collection_year, 6, 30)


def _decimal_or_none(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", "")
    if cleaned in {"", ".", "-"}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _csv_rows(artifact: FetchedArtifact) -> list[dict[str, str]]:
    if artifact.media_type == "application/zip" or artifact.locator.lower().endswith(".zip"):
        return _rows_from_zip(artifact.content)
    return _rows_from_csv_bytes(artifact.content)


def _rows_from_zip(content: bytes) -> list[dict[str, str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(members) != 1:
                raise SourceFetchError(
                    f"expected exactly one CSV member in IPEDS ZIP, found {len(members)}"
                )
            return _rows_from_csv_bytes(archive.read(members[0]))
    except zipfile.BadZipFile as exc:
        raise SourceFetchError("invalid IPEDS ZIP archive") from exc


def _rows_from_csv_bytes(content: bytes) -> list[dict[str, str]]:
    text: str
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise SourceFetchError("IPEDS CSV has no header")
    rows: list[dict[str, str]] = []
    for row in reader:
        normalized: dict[str, str] = {}
        for key, value in row.items():
            if key is None or isinstance(value, list):
                raise SourceFetchError("IPEDS CSV row does not match its header width")
            normalized[str(key)] = value or ""
        rows.append(normalized)
    return rows


def _require_fields(rows: Iterable[dict[str, str]], fields: set[str], label: str) -> None:
    rows = list(rows)
    if not rows:
        raise SourceFetchError(f"{label} contains no data rows")
    missing = fields - set(rows[0])
    if missing:
        raise SourceFetchError(f"{label} is missing required fields: {sorted(missing)}")
