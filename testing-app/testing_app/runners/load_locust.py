from __future__ import annotations

import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from testing_app.core.config import settings
from testing_app.services.artifacts import save_text_artifact


def _generate_locustfile(target: str, profile: dict[str, Any]) -> str:
    steps = profile.get("steps") or [{"method": "GET", "path": "/health"}]
    return f"""
from locust import HttpUser, task, between
import json

BASE = {target!r}
STEPS = {steps!r}

class WebsiteUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def flow(self):
        for s in STEPS:
            method = (s.get("method") or "GET").upper()
            path = s.get("path") or "/"
            body = s.get("body")
            headers = s.get("headers") or {{}}
            url = f"{{BASE.rstrip('/')}}{{path}}"
            if method in ("POST","PUT","PATCH"):
                self.client.request(method, url, json=body, headers=headers)
            else:
                self.client.request(method, url, headers=headers)
"""


def run_locust(run_id: int, target_api_url: str, profile: dict[str, Any]) -> dict[str, Any]:
    users = int(profile.get("users", 1))
    spawn_rate = float(profile.get("spawn_rate", 1))
    duration = str(profile.get("duration", "10s"))
    locustfile = _generate_locustfile(target_api_url, profile)
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        locust_path = work / "locustfile.py"
        out_std = work / "stdout.log"
        out_err = work / "stderr.log"
        locust_path.write_text(locustfile, encoding="utf-8")
        cmd = [
            "docker","run","--rm",
            "-v", f"{work}:/work",
            settings.locust_image,
            "-f","/work/locustfile.py",
            "--headless",
            "-u", str(users),
            "-r", str(spawn_rate),
            "--run-time", duration,
        ]
        cli = " ".join(shlex.quote(x) for x in cmd)
        try:
            res = subprocess.run(cmd, check=False, capture_output=True, text=True)
            out_std.write_text(res.stdout)
            out_err.write_text(res.stderr)
        except Exception as ex:
            save_text_artifact(run_id, "locust_error", str(ex))
            return {"tool": "locust", "error": str(ex)}
        artifacts = [
            save_text_artifact(run_id, "locustfile", locustfile),
            save_text_artifact(run_id, "locust_stdout", out_std.read_text()),
            save_text_artifact(run_id, "locust_stderr", out_err.read_text()),
        ]
        return {"tool": "locust", "cli": cli, "users": users, "spawn_rate": spawn_rate, "artifacts": artifacts}


