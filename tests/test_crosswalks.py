from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from mijobs.artifact_store import ArtifactStore
from mijobs.ingestion import Ingestor
from mijobs.ledger import audit_evidence_coverage, verify_ledger
from mijobs.sources.base import FetchedArtifact, SourceFetchError
from mijobs.sources.crosswalks import CIPSOC2020CrosswalkParser


def _artifact(content: bytes) -> FetchedArtifact:
    return FetchedArtifact(
        source_id="us_nces_ipeds",
        locator="https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.csv",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content=content,
        media_type="text/csv",
        dataset_version="CIP2020-SOC2018",
        parser_version="nces-cip2020-soc2018/1",
        metadata={"release_status": "official"},
    )


def test_cip_soc_parser_preserves_versions_titles_and_one_to_many() -> None:
    artifact = _artifact(
        b"CIP2020Code,CIP2020Title,SOC2018Code,SOC2018Title\n"
        b"11.0701,Computer Science,15-1252,Software Developers\n"
        b"11.0701,Computer Science,15-1211,Computer Systems Analysts\n"
        b"11.0701,Computer Science,15-1252,Software Developers\n"
    )
    mappings = CIPSOC2020CrosswalkParser().normalize(artifact)
    assert len(mappings) == 2
    assert mappings[0].from_system == "CIP"
    assert mappings[0].from_version == "2020"
    assert mappings[0].to_system == "SOC"
    assert mappings[0].to_version == "2018"
    assert mappings[0].weight is None
    assert mappings[0].metadata["cip_title"] == "Computer Science"


def test_crosswalk_ingestion_is_artifact_backed_and_ledgered(
    db_session: Session, tmp_path: Path
) -> None:
    artifact = _artifact(
        b"CIP2020Code\tCIP2020Title\tSOC2018Code\tSOC2018Title\n"
        b"15.0406\tAutomation Engineer Technology\t17-3024\tElectro-Mechanical Technicians\n"
    )
    record, mappings = Ingestor(db_session, ArtifactStore(tmp_path / "raw")).ingest_mappings(
        artifact, normalizer=CIPSOC2020CrosswalkParser().normalize
    )
    assert mappings[0].source_artifact_id == record.id
    assert mappings[0].mapping_key == "cip2020:15.0406:soc2018:17-3024"
    assert verify_ledger(db_session).event_count == 2
    assert audit_evidence_coverage(db_session).valid


def test_crosswalk_requires_schema() -> None:
    with pytest.raises(SourceFetchError):
        CIPSOC2020CrosswalkParser().normalize(_artifact(b"CIP2020Code\n11.0701\n"))
