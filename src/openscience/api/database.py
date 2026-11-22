"""Database engine and session management."""

from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all ORM models."""


_engine = None
_SessionLocal = None


def _enable_sqlite_foreign_keys(engine) -> None:
    """Enforce FOREIGN KEY constraints on every SQLite connection.

    SQLite ships with ``PRAGMA foreign_keys`` off, and it must be enabled
    per connection. Without this, FK constraints in the schema are parsed
    but never enforced, allowing orphaned rows.
    """

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_engine(database_url: str | None = None):
    """Create (once) and return the global SQLAlchemy engine."""
    global _engine
    if _engine is None or database_url is not None:
        if database_url is None:
            from openscience.api.config import get_settings

            database_url = get_settings().database_url
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        _engine = create_engine(database_url, connect_args=connect_args)
        if database_url.startswith("sqlite"):
            _enable_sqlite_foreign_keys(_engine)
        _reset_session_factory()
    return _engine


def _reset_session_factory() -> None:
    global _SessionLocal
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_session_factory():
    if _SessionLocal is None:
        get_engine()
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db(database_url: str | None = None) -> None:
    """Create all tables (used for tests/bootstrap; use Alembic in production)."""
    # Ensure models are imported so they register on the metadata.
    from openscience.api import models  # noqa: F401

    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)


def reset_engine() -> None:
    """Dispose of the engine and session factory (used in tests)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
