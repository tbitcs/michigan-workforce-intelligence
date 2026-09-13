from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from mijobs.db import initialize_database, make_engine, session_factory, session_scope
from mijobs.models import Claim


def test_session_scope_commits_and_rolls_back(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'scope.db'}")
    initialize_database(engine)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        session.add(
            Claim(
                id="1",
                claim_key="k",
                version=1,
                text="x",
                kind="reported",
                status="unresolved",
                scope_json={},
                quality_json={},
                supersedes_claim_id=None,
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
        )
    with factory() as session:
        assert session.scalar(select(Claim).where(Claim.id == "1")) is not None
    with pytest.raises(RuntimeError):
        _rollback(factory)
    with factory() as session:
        assert session.scalar(select(Claim).where(Claim.id == "2")) is None
    engine.dispose()


def _rollback(factory):
    with session_scope(factory) as session:
        session.add(
            Claim(
                id="2",
                claim_key="k2",
                version=1,
                text="x",
                kind="reported",
                status="unresolved",
                scope_json={},
                quality_json={},
                supersedes_claim_id=None,
                created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
        )
        raise RuntimeError("rollback")
