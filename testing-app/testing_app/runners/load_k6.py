from __future__ import annotations

import json
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from testing_app.core.config import settings
from testing_app.services.artifacts import save_json_artifact, save_text_artifact


def _build_options_js(profile: dict[str, Any], vus: int, duration: str) -> str:
    rate = profile.get("rate")
    if rate:
        pre_vus = int(profile.get("preAllocatedVUs", max(vus, 10)))
        return (
            "export const options = {\n"  # constant arrival rate scenario
            f"  scenarios: {{ requests: {{ executor: 'constant-arrival-rate', rate: {int(rate)}, timeUnit: '1s', duration: '{duration}', preAllocatedVUs: {pre_vus}, maxVUs: {pre_vus} }} }}\n"
            "};"
        )
    return f"export const options = {{ vus: {vus}, duration: '{duration}' }};"


def _generate_k6_script(target: str, profile: dict[str, Any]) -> str:
    vus = int(profile.get("vus", 1))
    duration = str(profile.get("duration", "10s"))
    endpoints = profile.get("endpoints") or ["/health"]
    steps: list[dict[str, Any]] = []
    for ep in endpoints:
        if isinstance(ep, str):
            steps.append({"method": "GET", "path": ep})
        elif isinstance(ep, dict):
            steps.append({
                "method": (ep.get("method") or "GET").upper(),
                "path": ep.get("path") or "/",
                "body": ep.get("body"),
                "headers": ep.get("headers") or {},
            })
    headers = profile.get("headers") or {}
    options = _build_options_js(profile, vus, duration)
    lines = [
        "import http from 'k6/http';",
        "import { sleep } from 'k6';",
        options,
        f"const BASE = '{target.rstrip('/')}';",
        f"const GH = {json.dumps(headers)};",
        f"const STEPS = {json.dumps(steps)};",
        "export default function () {",
        "  for (const s of STEPS){",
        "    const url = `${BASE}${s.path}`;",
        "    const h = Object.assign({}, GH, s.headers||{});",
        "    if (s.method === 'POST' || s.method === 'PUT' || s.method === 'PATCH') {",
        "      http.request(s.method, url, JSON.stringify(s.body||{}), { headers: Object.assign({'Content-Type':'application/json'}, h) });",
        "    } else {",
        "      http.request(s.method, url, null, { headers: h });",
        "    }",
        "  }",
        "  sleep(1);",
        "}",
    ]
    return "\n".join(lines)


def _parse_k6_summary(summary_text: str) -> dict[str, Any]:
    try:
        data = json.loads(summary_text)
    except Exception:
        return {}
    metrics = data.get("metrics", {})
    def _val(m: str, k: str) -> float | None:
        try:
            v = metrics[m][k]
            return float(v) if v is not None else None
        except Exception:
            return None
    http_reqs = _val("http_reqs", "count") or 0.0
    duration_avg = _val("http_req_duration", "avg")
    duration_p95 = _val("http_req_duration", "p(95)") or _val("http_req_duration", "p(95.00)")
    checks_pct = _val("checks", "passes")
    errors_pct = None
    if checks_pct is not None and http_reqs:
        # k6 'checks' is not strictly error rate; we skip if not provided
        pass
    return {
        "http_reqs": http_reqs,
        "avg_latency_ms": duration_avg,
        "p95_latency_ms": duration_p95,
        "rps": _val("http_reqs", "rate"),
        "error_rate": errors_pct,
    }


def run_k6(run_id: int, target_api_url: str, profile: dict[str, Any]) -> dict[str, Any]:
    script = _generate_k6_script(target_api_url, profile)
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        script_path = work / "script.js"
        out_summary = work / "summary.json"
        stdout_path = work / "stdout.log"
        stderr_path = work / "stderr.log"
        script_path.write_text(script, encoding="utf-8")
        cmd = [
            "docker","run","--rm",
            "-v", f"{work}:/work",
            settings.k6_image,
            "run","/work/script.js","--summary-export","/work/summary.json",
        ]
        cli = " ".join(shlex.quote(x) for x in cmd)
        try:
            res = subprocess.run(cmd, check=False, capture_output=True, text=True)
            stdout_path.write_text(res.stdout)
            stderr_path.write_text(res.stderr)
        except Exception as ex:
            save_text_artifact(run_id, "k6_error", str(ex))
            return {"tool": "k6", "error": str(ex), "artifacts": [save_text_artifact(run_id, "k6_script", script)]}

        artifacts: list[str] = []
        artifacts.append(save_text_artifact(run_id, "k6_script", script))
        artifacts.append(save_text_artifact(run_id, "k6_stdout", stdout_path.read_text()))
        artifacts.append(save_text_artifact(run_id, "k6_stderr", stderr_path.read_text()))
        stats: dict[str, Any] = {"tool": "k6", "cli": cli}
        if out_summary.exists():
            summary_text = out_summary.read_text(encoding="utf-8")
            artifacts.append(save_text_artifact(run_id, "k6_summary", summary_text))
            stats.update(_parse_k6_summary(summary_text))
        return {"stats": stats, "artifacts": artifacts}


