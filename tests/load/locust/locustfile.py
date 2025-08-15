from __future__ import annotations

import os
from locust import HttpUser, task, between


API = os.getenv("FORGE1_API_URL", "http://localhost:8000")
EMAIL = os.getenv("FORGE1_EMAIL", "demo@example.com")
PASSWORD = os.getenv("FORGE1_PASSWORD", "admin")


class ForgeUser(HttpUser):
    wait_time = between(0.1, 0.5)
    token: str | None = None

    def on_start(self) -> None:
        if os.getenv("FORGE1_TOKEN"):
            self.token = os.getenv("FORGE1_TOKEN")
        else:
            with self.client.post(f"{API}/api/v1/auth/login", data={"username": EMAIL, "password": PASSWORD}, catch_response=True) as res:
                try:
                    self.token = res.json().get("access_token")
                except Exception:
                    self.token = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def run_task(self) -> None:
        self.client.post(
            f"{API}/api/v1/ai/execute",
            json={"task": "Ping from Locust", "context": {}},
            headers=self._headers(),
        )

    @task(1)
    def metrics_summary(self) -> None:
        self.client.get(f"{API}/api/v1/metrics/summary", headers=self._headers())


