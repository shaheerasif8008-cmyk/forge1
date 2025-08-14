from __future__ import annotations

import os
import random
import string
from time import time

from locust import HttpUser, between, task


API_URL = os.getenv("FORGE_API_URL", "http://localhost:8000")
TOKEN = os.getenv("FORGE_TOKEN", "")


def _rand_name(prefix: str = "Emp") -> str:
    return f"{prefix}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"


class EmployeeUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:  # login or use provided token
        self.client.headers.update({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
        # Ensure at least one employee exists for this user
        resp = self.client.get(f"{API_URL}/api/v1/employees/")
        if resp.status_code == 200 and isinstance(resp.json(), list) and resp.json():
            self.employee_id = resp.json()[0]["id"]
        else:
            payload = {
                "name": _rand_name(),
                "role_name": "Sales Agent",
                "description": "load test agent",
                "tools": ["api_caller"],
            }
            r = self.client.post(f"{API_URL}/api/v1/employees/", json=payload)
            if r.status_code in (200, 201):
                self.employee_id = r.json()["id"]
            else:
                self.employee_id = None

    @task(5)
    def run_employee_task(self) -> None:
        if not getattr(self, "employee_id", None):
            return
        payload = {"task": "Summarize this: Forge 1 load test", "iterations": 1}
        self.client.post(f"{API_URL}/api/v1/employees/{self.employee_id}/run", json=payload, name="employee_run")

    @task(1)
    def list_models(self) -> None:
        self.client.get(f"{API_URL}/api/v1/ai/models", name="ai_models")


