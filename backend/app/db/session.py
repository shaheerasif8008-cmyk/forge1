from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import settings
from .models import Base


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


engine = create_engine(
    _make_engine_url(),
    pool_pre_ping=True,
    future=True,
    pool_size=getattr(settings, "db_pool_size", 5),
    max_overflow=getattr(settings, "db_max_overflow", 10),
    pool_recycle=getattr(settings, "db_pool_recycle", 1800),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


# Create tables if they don't exist
def create_tables() -> None:
    """Create all tables defined in models."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
