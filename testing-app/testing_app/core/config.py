from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final


ENV_PREFIX: Final[str] = "TESTING_"


@dataclass(frozen=True)
class Settings:
    db_url: str
    target_api_url_default: str
    service_key: str
    artifacts_url: str | None
    report_secret: str
    k6_image: str
    locust_image: str
    toxiproxy_url: str | None
    zap_image: str
    run_sync: bool

    @staticmethod
    def from_env() -> "Settings":
        # Prefer dedicated TESTING_DB_URL; fallback to existing app settings
        db_url = os.getenv(
            f"{ENV_PREFIX}DB_URL",
            os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:"),
        )

        return Settings(
            db_url=db_url,
            # Prefer TESTING_TARGET_API_URL_DEFAULT; fallback to TESTING_TARGET_API_URL; finally TARGET_API_URL
            target_api_url_default=(
                os.getenv(f"{ENV_PREFIX}TARGET_API_URL_DEFAULT")
                or os.getenv(f"{ENV_PREFIX}TARGET_API_URL")
                or os.getenv("TARGET_API_URL")
                or "http://localhost:8000"
            ),
            service_key=os.getenv(f"{ENV_PREFIX}SERVICE_KEY", ""),
            artifacts_url=os.getenv(f"{ENV_PREFIX}ARTIFACTS_URL"),
            report_secret=os.getenv(f"{ENV_PREFIX}REPORT_SECRET", "dev-secret"),
            k6_image=os.getenv(f"{ENV_PREFIX}K6_IMAGE", "grafana/k6:latest"),
            locust_image=os.getenv(f"{ENV_PREFIX}LOCUST_IMAGE", "locustio/locust:latest"),
            toxiproxy_url=os.getenv(f"{ENV_PREFIX}TOXIPROXY_URL"),
            zap_image=os.getenv(f"{ENV_PREFIX}ZAP_IMAGE", "owasp/zap2docker-stable"),
            run_sync=os.getenv("TESTING", "0") == "1" or os.getenv(f"{ENV_PREFIX}RUN_SYNC", "0") == "1",
        )


settings = Settings.from_env()

BASE_ARTIFACTS_DIR: Final[Path] = Path(os.getenv("TESTING_ARTIFACTS_DIR", Path.cwd() / "artifacts"))
BASE_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


