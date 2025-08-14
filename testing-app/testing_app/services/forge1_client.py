from __future__ import annotations

from typing import Any

import httpx


class Forge1ControlPlane:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        hdrs: dict[str, str] = {"Accept": "application/json"}
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        return hdrs

    def dry_run(self) -> dict[str, Any]:
        # Placeholder dry-run using mode endpoint; can extend per real API
        url = f"{self.base_url}/api/v1/admin/release/mode"
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, headers=self._headers())
            r.raise_for_status()
            return r.json()

    def promote(self, percent: int = 100) -> dict[str, Any]:
        url = f"{self.base_url}/api/v1/admin/release/percent"
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json={"percent": percent}, headers=self._headers())
            r.raise_for_status()
            return r.json()

    def rollback(self) -> dict[str, Any]:
        url = f"{self.base_url}/api/v1/admin/release/rollback"
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, headers=self._headers())
            r.raise_for_status()
            return r.json()

    def set_chaos_mode(self, enabled: bool, error_pct: float = 0.01, db_delay_ms: int = 0, redis_timeout_pct: float = 0.0) -> dict[str, Any]:
        # Optional endpoint if Forge1 exposes it; best-effort
        url = f"{self.base_url}/api/v1/admin/chaos"
        payload = {"enabled": bool(enabled), "error_pct": float(error_pct), "db_delay_ms": int(db_delay_ms), "redis_timeout_pct": float(redis_timeout_pct)}
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(url, json=payload, headers=self._headers())
                if r.status_code in (200, 201, 204):
                    return {"status": "ok"}
        except Exception:
            pass
        return {"status": "noop"}


