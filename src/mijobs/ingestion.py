from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from mijobs.artifact_store import ArtifactStore
from mijobs.domain import ObservationInput, TaxonomyMappingInput
from mijobs.models import Observation, SourceArtifact, TaxonomyMapping
from mijobs.repository import EvidenceRepository
from mijobs.sources.base import FetchedArtifact

Normalizer = Callable[[FetchedArtifact], list[ObservationInput]]
MappingNormalizer = Callable[[FetchedArtifact], list[TaxonomyMappingInput]]


class Ingestor:
    def __init__(self, session: Session, store: ArtifactStore, *, actor: str = "ingestor"):
        self.session = session
        self.store = store
        self.repo = EvidenceRepository(session, actor=actor)

    def ingest(
        self,
        artifact: FetchedArtifact,
        *,
        normalizer: Normalizer | None = None,
    ) -> tuple[SourceArtifact, list[Observation]]:
        stored = self.store.put(artifact.content)
        record = self.repo.add_source_artifact(
            source_id=artifact.source_id,
            source_locator=artifact.locator,
            retrieved_at=artifact.retrieved_at,
            content_sha256=stored.sha256,
            media_type=artifact.media_type,
            byte_size=stored.byte_size,
            local_path=str(stored.path),
            dataset_version=artifact.dataset_version,
            parser_version=artifact.parser_version,
            metadata={**artifact.metadata, "content_addressed_created": stored.created},
        )
        observations: list[Observation] = []
        if normalizer is not None:
            for item in normalizer(artifact):
                observations.append(self.repo.add_observation(record.id, item))
        return record, observations

    def ingest_mappings(
        self,
        artifact: FetchedArtifact,
        *,
        normalizer: MappingNormalizer,
    ) -> tuple[SourceArtifact, list[TaxonomyMapping]]:
        record, _ = self.ingest(artifact)
        mappings = [
            self.repo.add_taxonomy_mapping_input(record.id, item)
            for item in normalizer(artifact)
        ]
        return record, mappings

