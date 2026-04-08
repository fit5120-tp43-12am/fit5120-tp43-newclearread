from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text  # type: ignore[import-not-found]
from sqlalchemy.engine import Engine  # type: ignore[import-not-found]
from sqlalchemy.orm import Session, sessionmaker  # type: ignore[import-not-found]


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def build_database_url() -> str:
    """
    Build a SQLAlchemy MySQL URL.

    Supports either:
    - DATABASE_URL (full URL), or
    - DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME
    """
    full = _env("DATABASE_URL")
    if full:
        return full

    host = _env("DB_HOST", "127.0.0.1")
    port = int(_env("DB_PORT", "3306") or 3306)
    user = _env("DB_USER", "root")
    password = _env("DB_PASSWORD", "")
    db = _env("DB_NAME", "clearread")

    # PyMySQL driver is present in this repo's venv.
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


_ENGINE: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    global _ENGINE, SessionLocal
    if _ENGINE is not None and SessionLocal is not None:
        return _ENGINE

    url = build_database_url()
    _ENGINE = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=int(_env("DB_POOL_RECYCLE_SECONDS", "1800") or 1800),
        pool_size=int(_env("DB_POOL_SIZE", "5") or 5),
        max_overflow=int(_env("DB_MAX_OVERFLOW", "10") or 10),
        future=True,
    )
    SessionLocal = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False, future=True)
    return _ENGINE


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency: yields a SQLAlchemy session and closes it afterwards.
    """
    engine = get_engine()
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Convenience context manager for non-FastAPI code paths.
    """
    engine = get_engine()
    assert SessionLocal is not None
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection() -> None:
    """
    Raises if the DB is unreachable.
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
