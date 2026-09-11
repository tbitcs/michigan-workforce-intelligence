from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from mijobs.db import initialize_database, make_engine, session_factory


@pytest.fixture
def db_session(tmp_path: Path) -> Session:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    initialize_database(engine)
    factory = session_factory(engine)
    with factory() as session:
        yield session
        session.rollback()
    engine.dispose()
