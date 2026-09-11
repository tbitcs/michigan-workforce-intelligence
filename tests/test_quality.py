import pytest

from mijobs.analytics.quality import EvidenceQuality


def test_quality_is_decomposed_and_bounded() -> None:
    quality = EvidenceQuality(1.0, 0.9, 0.8, 0.7, 1.0, 0.6)
    result = quality.as_dict()
    assert 0 < result["aggregate"] < 1
    assert result["source_authority"] == 1.0


def test_zero_dimension_caps_score_at_zero() -> None:
    assert EvidenceQuality(1, 1, 1, 1, 1, 0).score() == 0


def test_invalid_quality_rejected() -> None:
    with pytest.raises(ValueError):
        EvidenceQuality(1.1, 1, 1, 1, 1, 1)
