from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import settings


def _make_engine_url() -> str:
    url = settings.database_url
    # Prefer psycopg (v3) when available on newer Python; fallback to psycopg2
    try:
        import psycopg  # noqa: F401

        preferred_driver = "+psycopg"
    except Exception:  # noqa: BLE001
        preferred_driver = "+psycopg2"

    if url.startswith("postgresql://") and preferred_driver not in url:
        url = url.replace("postgresql://", f"postgresql{preferred_driver}://", 1)
    return url


engine = create_engine(_make_engine_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


