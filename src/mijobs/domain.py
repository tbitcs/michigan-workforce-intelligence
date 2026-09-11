from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ClaimKind(StrEnum):
    REPORTED = "reported"
    DERIVED = "derived"
    INFERRED = "inferred"
    ESTIMATED = "estimated"
    PROJECTED = "projected"
    HYPOTHESIS = "hypothesis"


class ClaimStatus(StrEnum):
    SUPPORTED = "supported"
    WEAKLY_SUPPORTED = "weakly_supported"
    CONTESTED = "contested"
    CONTRADICTED = "contradicted"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    UNRESOLVED = "unresolved"


class EvidenceRelation(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    DERIVES_FROM = "derives_from"


class EvidenceType(StrEnum):
    OBSERVATION = "observation"
    CLAIM = "claim"
    ARTIFACT = "artifact"
    DERIVED_METRIC = "derived_metric"


class ChallengeStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    WITHDRAWN = "withdrawn"


class MappingRelation(StrEnum):
    EXACT = "exact"
    BROADER = "broader"
    NARROWER = "narrower"
    RELATED = "related"


@dataclass(frozen=True, slots=True)
class TaxonomyMappingInput:
    mapping_key: str
    from_system: str
    from_version: str
    from_code: str
    to_system: str
    to_version: str
    to_code: str
    relation: MappingRelation = MappingRelation.RELATED
    weight: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ObservationInput:
    observation_key: str
    metric: str
    value_text: str
    unit: str
    numeric_value: Decimal | None = None
    geography_type: str | None = None
    geography_code: str | None = None
    geography_name: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    period_basis: str | None = None
    taxonomy_system: str | None = None
    taxonomy_version: str | None = None
    taxonomy_code: str | None = None
    adjustment: str | None = None
    release_status: str | None = None
    uncertainty: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
