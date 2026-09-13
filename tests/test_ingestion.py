from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from mijobs.artifact_store import ArtifactStore
from mijobs.domain import ObservationInput
from mijobs.ingestion import Ingestor
from mijobs.ledger import verify_ledger
from mijobs.sources.base import FetchedArtifact


def test_ingestor_saves_exact_bytes_and_normalized_observation(
    db_session: Session, tmp_path: Path
) -> None:
    artifact = FetchedArtifact(
        source_id="mi_mcda_laus",
        locator="https://www.michigan.gov/example.csv",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content=b"exact,official,bytes\n",
        media_type="text/csv",
        dataset_version="2026-08",
        parser_version="test/1",
    )

    def normalize(_: FetchedArtifact) -> list[ObservationInput]:
        return [
            ObservationInput(
                observation_key="mi:laus:rate:2026-08",
                metric="unemployment_rate",
                value_text="5.1",
                numeric_value=Decimal("5.1"),
                unit="percent",
                geography_type="state",
                geography_code="26",
                geography_name="Michigan",
            )
        ]

    record, observations = Ingestor(db_session, ArtifactStore(tmp_path / "raw")).ingest(
        artifact, normalizer=normalize
    )
    assert Path(record.local_path).read_bytes() == artifact.content
    assert observations[0].source_artifact_id == record.id
    assert observations[0].numeric_value == 5.1
    assert verify_ledger(db_session).event_count == 2


def test_reingesting_same_bytes_reuses_content_addressed_file(
    db_session: Session, tmp_path: Path
) -> None:
    artifact = FetchedArtifact(
        source_id="mi_mcda_laus",
        locator="https://www.michigan.gov/example.csv",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        content=b"same bytes",
        media_type="text/csv",
    )
    ingestor = Ingestor(db_session, ArtifactStore(tmp_path / "raw"))
    first, _ = ingestor.ingest(artifact)
    second, _ = ingestor.ingest(artifact)
    assert first.content_sha256 == second.content_sha256
    assert first.id != second.id
    assert second.metadata_json["content_addressed_created"] is False
