from datetime import datetime, timezone
from decimal import Decimal

import pytest

from mijobs.canonical import CanonicalizationError, canonical_json, canonical_sha256


def test_canonical_json_is_order_independent() -> None:
    left = {"b": 2, "a": [Decimal("1.00"), datetime(2026, 9, 11, tzinfo=timezone.utc)]}
    right = {"a": [Decimal("1.0"), datetime(2026, 9, 11, tzinfo=timezone.utc)], "b": 2}
    assert canonical_json(left) == canonical_json(right)
    assert canonical_sha256(left) == canonical_sha256(right)


def test_canonical_rejects_nonfinite_float() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json({"x": float("nan")})


def test_canonical_supports_evidence_value_types(tmp_path) -> None:
    from datetime import date
    from enum import Enum
    from pathlib import Path
    from uuid import UUID

    class Kind(Enum):
        A = "a"

    payload = {
        "date": date(2026, 9, 11),
        "path": Path("a/b"),
        "uuid": UUID("00000000-0000-0000-0000-000000000001"),
        "enum": Kind.A,
        "bytes": b"abc",
    }
    encoded = canonical_json(payload)
    assert '"date":"2026-09-11"' in encoded
    assert '"path":"a/b"' in encoded
    assert '"enum":"a"' in encoded
    assert "$bytes_sha256" in encoded


def test_canonical_rejects_invalid_decimal_key_and_object() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json({"x": Decimal("NaN")})
    with pytest.raises(CanonicalizationError):
        canonical_json({1: "not-string-key"})
    with pytest.raises(CanonicalizationError):
        canonical_json({"x": object()})
