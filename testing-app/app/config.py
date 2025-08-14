from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env.testing"


def load_env() -> None:
    # Load .env.testing if present
    load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    vector_namespace_prefix: str
    log_level: str

    @staticmethod
    def from_env() -> "Settings":
        load_env()
        if os.getenv("TESTING") == "1":
            db_url = "sqlite+pysqlite:///:memory:"
        else:
            db_url = os.getenv(
                "DATABASE_URL", "postgresql+psycopg://forge:forge@localhost:5542/forge1_testing"
            )
        return Settings(
            database_url=db_url,
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6380/1"),
            vector_namespace_prefix=os.getenv("VECTOR_NAMESPACE_PREFIX", "testing_"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


settings = Settings.from_env()
