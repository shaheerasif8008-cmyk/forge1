from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from testing_app.core.config import settings
from testing_app.services.artifacts import save_text_artifact, save_text_artifact_ext


def _risk_to_severity(risk: str) -> str:
    m = (risk or "").lower()
    if m.startswith("high"):
        return "high"
    if m.startswith("medium"):
        return "medium"
    return "low"


def run_zap_baseline(run_id: int, api_url: str | None, ui_url: str | None, ignore_rules: list[str] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    stats: dict[str, Any] = {}
    targets: list[str] = []
    if api_url:
        targets.append(api_url)
    if ui_url:
        targets.append(ui_url)
    ignore_rules = ignore_rules or []
    for target in targets:
        try:
            with _tmpdir() as td:
                work = Path(td)
                cmd = [
                    "docker","run","--rm",
                    "-v", f"{work}:/zap/wrk",
                    settings.zap_image,
                    "zap-baseline.py","-t",target,"-r","report.html","-J","report.json","-m", "10",
                ]
                res = subprocess.run(cmd, check=False, capture_output=True, text=True)
                save_text_artifact(run_id, f"zap_{_safe_name(target)}_stdout", res.stdout)
                save_text_artifact(run_id, f"zap_{_safe_name(target)}_stderr", res.stderr)
                # Persist HTML report if present
                report_html = work / "report.html"
                if report_html.exists():
                    url = save_text_artifact_ext(run_id, f"zap_{_safe_name(target)}_report", report_html.read_text(encoding="utf-8"), "html")
                # Parse JSON alerts
                report_json = work / "report.json"
                if report_json.exists():
                    data = json.loads(report_json.read_text(encoding="utf-8"))
                    for a in data.get("site", []):
                        alerts = a.get("alerts", [])
                        for al in alerts:
                            risk = str(al.get("riskdesc", ""))
                            sev = _risk_to_severity(risk)
                            name = al.get("name", "")
                            if any(rule for rule in ignore_rules if rule and rule in str(name)):
                                continue
                            if sev in {"high", "medium"}:
                                findings.append({
                                    "severity": sev,
                                    "area": target,
                                    "message": f"{name} ({risk})",
                                    "trace_id": None,
                                    "suggested_fix": "Review ZAP alert and mitigate",
                                })
        except Exception as ex:
            save_text_artifact(run_id, f"zap_{_safe_name(target)}_error", str(ex))
            findings.append({
                "severity": "low",
                "area": target,
                "message": str(ex),
                "trace_id": None,
                "suggested_fix": "Ensure target is reachable and ZAP image available",
            })
    stats["targets"] = targets
    return stats, findings


from contextlib import contextmanager
import tempfile


@contextmanager
def _tmpdir():  # pragma: no cover - trivial
    d = tempfile.TemporaryDirectory()
    try:
        yield d.name
    finally:
        d.cleanup()


def _safe_name(url: str) -> str:
    return url.replace("://", "_").replace("/", "_")


