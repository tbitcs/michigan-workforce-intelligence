from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from mijobs.config import load_source_catalog
from mijobs.domain import MappingRelation
from mijobs.ledger import audit_evidence_coverage, verify_ledger
from mijobs.mcp_service import MCPService
from mijobs.repository import EvidenceRepository


def _artifact(repo: EvidenceRepository):
    return repo.add_source_artifact(
        source_id="us_nces_ipeds",
        source_locator="https://nces.ed.gov/example-crosswalk.csv",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content_sha256="d" * 64,
        media_type="text/csv",
        byte_size=10,
        local_path="dd/dd/hash",
        dataset_version="2020-CIP-to-2018-SOC",
    )


def test_taxonomy_mapping_versions_and_ledgers(db_session: Session) -> None:
    repo = EvidenceRepository(db_session, actor="crosswalk")
    artifact = _artifact(repo)
    first = repo.add_taxonomy_mapping(
        mapping_key="cip:15.0406:soc:17-3024",
        source_artifact_id=artifact.id,
        from_system="CIP",
        from_version="2020",
        from_code="15.0406",
        to_system="SOC",
        to_version="2018",
        to_code="17-3024",
        relation=MappingRelation.RELATED,
        weight=0.8,
    )
    second = repo.add_taxonomy_mapping(
        mapping_key="cip:15.0406:soc:17-3024",
        source_artifact_id=artifact.id,
        from_system="CIP",
        from_version="2020",
        from_code="15.0406",
        to_system="SOC",
        to_version="2018",
        to_code="17-3024",
        relation=MappingRelation.RELATED,
        weight=0.9,
        metadata={"revision": "reviewed"},
    )
    assert second.version == 2
    assert second.supersedes_mapping_id == first.id
    assert repo.latest_taxonomy_mapping(first.mapping_key).id == second.id
    assert verify_ledger(db_session).valid
    assert audit_evidence_coverage(db_session).valid


def test_mapping_weight_is_bounded(db_session: Session) -> None:
    repo = EvidenceRepository(db_session)
    artifact = _artifact(repo)
    with pytest.raises(ValueError):
        repo.add_taxonomy_mapping(
            mapping_key="bad",
            source_artifact_id=artifact.id,
            from_system="CIP",
            from_version="2020",
            from_code="x",
            to_system="SOC",
            to_version="2018",
            to_code="y",
            weight=1.1,
        )


def test_mcp_mapping_search_returns_latest_version(db_session: Session) -> None:
    repo = EvidenceRepository(db_session)
    artifact = _artifact(repo)
    for weight in (0.5, 0.7):
        repo.add_taxonomy_mapping(
            mapping_key="crosswalk",
            source_artifact_id=artifact.id,
            from_system="CIP",
            from_version="2020",
            from_code="11.0701",
            to_system="SOC",
            to_version="2018",
            to_code="15-1252",
            weight=weight,
        )
    service = MCPService(db_session, load_source_catalog())
    result = service.mappings_search(from_system="CIP", from_code="11.0701")
    assert result["count"] == 1
    assert result["mappings"][0]["weight"] == 0.7
    assert service.mappings_search(from_system="CIP", latest_only=False)["count"] == 2
