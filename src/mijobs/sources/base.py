from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class SourceFetchError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FetchedArtifact:
    source_id: str
    locator: str
    retrieved_at: datetime
    content: bytes
    media_type: str
    dataset_version: str | None = None
    parser_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceConnector(ABC):
    source_id: str

    @abstractmethod
    def healthcheck(self) -> bool:
        raise NotImplementedError
