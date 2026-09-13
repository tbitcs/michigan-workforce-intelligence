from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from mijobs.models import Base

IMMUTABLE_TABLES = (
    "source_artifacts",
    "observations",
    "claims",
    "evidence_edges",
    "challenges",
    "taxonomy_mappings",
    "derived_metrics",
    "ledger_events",
)


def make_engine(database_url: str, *, echo: bool = False) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, echo=echo, future=True, connect_args=connect_args)
    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _sqlite_foreign_keys)
    return engine


def _sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            for table in IMMUTABLE_TABLES:
                connection.execute(
                    text(
                        f"""
                        CREATE TRIGGER IF NOT EXISTS {table}_no_update
                        BEFORE UPDATE ON {table}
                        BEGIN
                          SELECT RAISE(ABORT, '{table} is append-only');
                        END;
                        """
                    )
                )
                connection.execute(
                    text(
                        f"""
                        CREATE TRIGGER IF NOT EXISTS {table}_no_delete
                        BEFORE DELETE ON {table}
                        BEGIN
                          SELECT RAISE(ABORT, '{table} is append-only');
                        END;
                        """
                    )
                )


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
