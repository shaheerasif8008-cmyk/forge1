from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from testing_app.core.config import settings


def _create_engine():
    url = settings.db_url
    if url.startswith("sqlite") and ":memory:" in url:
        eng = create_engine(
            url,
            pool_pre_ping=True,
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Translate schema "testing" to None for SQLite
        return eng.execution_options(schema_translate_map={"testing": None})
    eng = create_engine(url, pool_pre_ping=True, future=True)
    if eng.url.get_backend_name().startswith("sqlite"):
        eng = eng.execution_options(schema_translate_map={"testing": None})
    return eng


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def ensure_schema() -> None:
    if engine.url.get_backend_name().startswith("postgresql"):
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS testing"))


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


