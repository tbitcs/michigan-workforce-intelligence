from __future__ import annotations

import math
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class EvidenceQuality:
    """Decomposed evidence quality; each component is in [0, 1]."""

    source_authority: float
    directness: float
    methodological_fit: float
    temporal_relevance: float
    reproducibility: float
    uncertainty_quality: float

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0,1]")

    def score(self) -> float:
        # Geometric mean makes a serious weakness matter instead of letting strong
        # dimensions fully compensate for it. Zero remains zero.
        values = list(asdict(self).values())
        if any(value == 0.0 for value in values):
            return 0.0
        return float(math.prod(values) ** (1.0 / len(values)))

    def as_dict(self) -> dict[str, float]:
        result = {key: float(value) for key, value in asdict(self).items()}
        result["aggregate"] = self.score()
        return result
