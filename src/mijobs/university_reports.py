"""Official university evidence preparation and read-only report context."""
from __future__ import annotations

import csv
import io
import json
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from mijobs.artifact_store import ArtifactStore
from mijobs.domain import ObservationInput
from mijobs.ingestion import Ingestor
from mijobs.ledger import audit_evidence_coverage, verify_ledger
from mijobs.models import Observation, SourceArtifact, TaxonomyMapping
from mijobs.sources.base import FetchedArtifact
from mijobs.sources.crosswalks import CIPSOC2020CrosswalkParser
from mijobs.sources.http_policy import governed_client
from mijobs.sources.institutions import PARTNER_INSTITUTIONS, PARTNER_UNITIDS
from mijobs.sources.ipeds import IPEDSConnector

CROSSWALK_URL = "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx"
PSEO_COVERAGE_URL = "https://lehd.ces.census.gov/data/pseo/latest_release/mi/pseo_mi_institutions.csv"

SCORECARD_URL = "https://api.data.gov/ed/collegescorecard/v1/schools.json"
SCORECARD_FIELDS = {
    "2020.earnings.10_yrs_after_entry.median": ("scorecard.earnings.10_years_after_entry.median", "USD", 2020),
    "2024.completion.completion_rate_4yr_150nt": ("scorecard.completion.4yr_150pct", "fraction", 2024),
}


def scorecard_observations(artifact: FetchedArtifact) -> list[ObservationInput]:
    rows = json.loads(artifact.content)["results"]
    if {str(row["id"]) for row in rows} != set(PARTNER_UNITIDS):
        raise ValueError("Scorecard response must cover all configured institutions")
    observations = []
    for row in rows:
        for field, (metric, unit, year) in SCORECARD_FIELDS.items():
            value = row[field]
            observations.append(ObservationInput(observation_key=f"scorecard:{row['id']}:{field}",
                metric=metric, value_text=str(value) if value is not None else "unknown",
                numeric_value=Decimal(str(value)) if value is not None else None, unit=unit,
                geography_type="institution", geography_code=str(row["id"]),
                period_basis="scorecard_api_data_year", release_status="published",
                metadata={"api_field": field, "data_year": year,
                          "cohort_note": "Earnings: federally aided entrants working and not enrolled, ten years after entry. Completion: first-time full-time students within 150% normal time. API data year is not an earnings-calendar-year assertion.",
                          "documentation": "https://collegescorecard.ed.gov/files/InstitutionDataDocumentation.pdf"}))
    return observations


def require_audit(session: Session) -> None:
    if not verify_ledger(session).valid or not audit_evidence_coverage(session).valid:
        raise RuntimeError("Refusing university operation with unaudited evidence")


def harvest_universities(session: Session, store: ArtifactStore, *, year: int = 2024) -> dict[str, Any]:
    require_audit(session)
    ingestor = Ingestor(session, store, actor="university-harvest")
    with governed_client(timeout=120, follow_redirects=True) as client:
        connector = IPEDSConnector(client)
        completions = connector.fetch_data_file(f"C{year}_A.zip", collection_year=year, release_status="provisional")
        raw, observations = ingestor.ingest(completions, normalizer=lambda a: connector.normalize_completions(
            a, collection_year=year, cip_version="2020", allowed_unitids=set(PARTNER_UNITIDS)))
        if {o.geography_code for o in observations} != set(PARTNER_UNITIDS):
            raise ValueError("IPEDS file does not cover every configured institution")
        response = client.get(CROSSWALK_URL)
        response.raise_for_status()
        crosswalk = FetchedArtifact(source_id="us_nces_ipeds", locator=CROSSWALK_URL,
            retrieved_at=datetime.now(UTC), content=response.content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            dataset_version="CIP2020-SOC2018", parser_version=CIPSOC2020CrosswalkParser.parser_version)
        mapping_artifact, mappings = ingestor.ingest_mappings(crosswalk, normalizer=CIPSOC2020CrosswalkParser().normalize)
        response = client.get(PSEO_COVERAGE_URL)
        response.raise_for_status()
        coverage = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        if not coverage or not {"institution", "label"}.issubset(coverage[0]):
            raise ValueError("Unrecognized PSEO institution coverage schema")
        coverage_artifact, _ = ingestor.ingest(FetchedArtifact(source_id="us_census_pseo",
            locator=PSEO_COVERAGE_URL, retrieved_at=datetime.now(UTC), content=response.content,
            media_type="text/csv", parser_version="pseo-coverage/1", metadata={"institutions": coverage}))
        params = {"id": ",".join(sorted(PARTNER_UNITIDS)), "fields": ",".join(["id", "school.name", *SCORECARD_FIELDS]), "per_page": "10"}
        response = client.get(SCORECARD_URL, params={**params, "api_key": os.getenv("SCORECARD_API_KEY", "DEMO_KEY")})
        if response.status_code != 200:
            raise ValueError(f"Scorecard HTTP {response.status_code}; check SCORECARD_API_KEY or rate limits")
        scorecard_artifact, outcomes = ingestor.ingest(FetchedArtifact(source_id="us_ed_scorecard",
            locator=SCORECARD_URL + "?query=" + json.dumps(params, sort_keys=True),
            retrieved_at=datetime.now(UTC), content=response.content, media_type="application/json",
            parser_version="scorecard-outcomes/1", metadata={"request": params}), normalizer=scorecard_observations)
    require_audit(session)
    return {"year": year, "observations": len(observations), "mappings": len(mappings),
            "outcomes": len(outcomes), "artifact_ids": [raw.id, mapping_artifact.id, coverage_artifact.id, scorecard_artifact.id], "pseo_coverage": coverage}


def university_report(session: Session, *, year: int = 2024) -> dict[str, Any]:
    require_audit(session)
    newer = aliased(Observation)
    rows = list(session.scalars(select(Observation).where(
        Observation.metric == "ipeds.completions.awards",
        ~select(newer.id).where(newer.observation_key == Observation.observation_key,
                               newer.version > Observation.version).exists())))
    outcomes = list(session.scalars(select(Observation).where(Observation.metric.like("scorecard.%"),
        ~select(newer.id).where(newer.observation_key == Observation.observation_key,
                               newer.version > Observation.version).exists())))
    mappings = list(session.scalars(select(TaxonomyMapping).where(
        TaxonomyMapping.from_system == "CIP", TaxonomyMapping.from_version == "2020",
        TaxonomyMapping.to_system == "SOC", TaxonomyMapping.to_version == "2018")))
    links: dict[str, set[str]] = {}
    for mapping in mappings:
        links.setdefault(mapping.from_code, set()).add(mapping.to_code)
    institutions = []
    artifact_ids: set[str] = set()
    for institution in PARTNER_INSTITUTIONS:
        selected = [o for o in rows if o.geography_code == institution.unitid
                    and o.metadata_json.get("collection_year") == year
                    and o.metadata_json.get("major_number") == "1"
                    and re.fullmatch(r"\d{2}\.\d{4}", o.taxonomy_code or "")
                    and o.taxonomy_code != "99.0000"]
        programs = []
        for o in selected:
            artifact_ids.add(o.source_artifact_id)
            programs.append({"cip_code": o.taxonomy_code, "award_level": o.metadata_json["award_level"],
                             "awards": o.numeric_value, "observation_id": o.id,
                             "artifact_id": o.source_artifact_id,
                             "related_soc_codes": sorted(links.get(o.taxonomy_code or "", set()))})
        missing_values = any(o.numeric_value is None for o in selected)
        institution_outcomes = [o for o in outcomes if o.geography_code == institution.unitid]
        artifact_ids.update(o.source_artifact_id for o in institution_outcomes)
        institutions.append({"unitid": institution.unitid, "name": institution.name,
                             "status": "available" if selected and not missing_values else "insufficient_data",
                             "total_first_major_awards": sum(o.numeric_value or 0 for o in selected) if selected and not missing_values else None,
                             "programs": programs,
                             "outcomes": [{"metric": o.metric, "value": o.numeric_value, "unit": o.unit,
                                "data_year": o.metadata_json["data_year"], "observation_id": o.id,
                                "artifact_id": o.source_artifact_id, "cohort_note": o.metadata_json["cohort_note"]} for o in institution_outcomes],
                             "employment_outcomes_status": "scorecard_available" if institution_outcomes else "not_loaded",
                             "michigan_retention_status": "not_available"})
    for mapping in mappings:
        artifact_ids.add(mapping.source_artifact_id)
    coverage = session.scalar(select(SourceArtifact).where(SourceArtifact.source_id == "us_census_pseo",
        SourceArtifact.parser_version == "pseo-coverage/1").order_by(SourceArtifact.retrieved_at.desc()).limit(1))
    if coverage:
        artifact_ids.add(coverage.id)
    artifacts = [session.get(SourceArtifact, artifact_id) for artifact_id in sorted(artifact_ids)]
    return {"schema": "mijobs-university-report/v1", "collection_year": year,
            "academic_period": f"{year - 1}-07-01 through {year}-06-30", "institutions": institutions,
            "pseo_coverage": coverage.metadata_json.get("institutions", []) if coverage else [],
            "artifacts": [{"id": a.id, "url": a.source_locator, "sha256": a.content_sha256,
                           "retrieved_at": a.retrieved_at.isoformat()} for a in artifacts if a],
            "ledger": {"valid": True, "head_hash": verify_ledger(session).head_hash},
            "caveats": ["Awards are credentials, not unique graduates or employment outcomes.",
                        "Only first majors and six-digit program rows are summed; aggregate CIP totals are excluded.",
                        "IPEDS imputed values retain source flags in observation metadata.",
                        "Related SOC codes describe possible pathways, not measured placements or job demand.",
                        "Census PSEO uses OPEIDs, not IPEDS UnitIDs. Consult the attached coverage list.",
                        "Employment, earnings and Michigan retention are not inferred from academic awards."]}
