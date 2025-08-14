from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from testing_app.db.session import SessionLocal, engine, ensure_schema
from testing_app.models import Base
from testing_app.models.entities import ChaosExperiment, Finding, LoadJob, RunStatus, TestRun
from testing_app.runners.functional import execute_functional_suite
from testing_app.runners.load_k6 import run_k6
from testing_app.runners.load_locust import run_locust
from testing_app.runners.chaos import run_chaos_profile, start_experiment, stop_experiment, ChaosHandle
from testing_app.runners.zap import run_zap_baseline
from testing_app.services.reports import try_write_pdf_report, write_html_report
from testing_app.worker.celery_app import celery_app


def _init_db() -> None:
    ensure_schema()
    Base.metadata.create_all(bind=engine)


@celery_app.task(name="testing_app.run_suite")
def run_suite_task(run_id: int, suite: dict[str, Any]) -> dict[str, Any]:
    _init_db()
    db: Session = SessionLocal()
    try:
        run = db.get(TestRun, run_id)
        if run is None:
            return {"error": "run not found"}
        # Emit start event (best-effort)
        try:
            import asyncio as _asyncio
            from app.interconnect import get_interconnect  # type: ignore
            async def _emit_start():
                ic = await get_interconnect()
                await ic.publish(stream="events.ops", type="testpack.started", source="testing_app", data={"run_id": run.id, "suite": suite.get("name")})
            _asyncio.get_event_loop().create_task(_emit_start())
        except Exception:
            pass
        # Functional
        stats_total: dict[str, Any] = {}
        findings_all: list[dict[str, Any]] = []
        scenarios = suite.get("scenarios", [])
        if scenarios:
            s, f = execute_functional_suite(run_id, run.target_api_url, scenarios)
            stats_total["functional"] = s
            findings_all.extend(f)
        # Load
        load_profile = suite.get("load_profile") or {}
        if load_profile.get("tool") == "k6":
            k6res = run_k6(run_id, run.target_api_url, load_profile)
            stats_total["load_k6"] = k6res.get("stats", {})
            run.artifacts = (run.artifacts or []) + list(k6res.get("artifacts", []))
        elif load_profile.get("tool") == "locust":
            lres = run_locust(run_id, run.target_api_url, load_profile)
            stats_total["load_locust"] = {
                "users": lres.get("users"),
                "spawn_rate": lres.get("spawn_rate"),
            }
            run.artifacts = (run.artifacts or []) + list(lres.get("artifacts", []))

        # Chaos
        chaos_profile = suite.get("chaos_profile") or {}
        chaos_handle: ChaosHandle | None = None
        if chaos_profile:
            # Start experiment and rewrite target URL if proxy provided
            ch_stats, handle = start_experiment(run.target_api_url, chaos_profile)
            chaos_handle = handle
            if ch_stats.get("proxy_url"):
                run.target_api_url = str(ch_stats["proxy_url"])  # route load/functional through proxy
            stats_total["chaos"] = ch_stats

        # Security
        security_profile = suite.get("security_profile") or {}
        if security_profile:
            api_url = security_profile.get("api_url")
            ui_url = security_profile.get("ui_url")
            ignore = list(security_profile.get("ignore", [])) if isinstance(security_profile.get("ignore", []), list) else []
            zs, zf = run_zap_baseline(run_id, api_url, ui_url, ignore_rules=ignore)
            stats_total["zap"] = zs
            findings_all.extend(zf)

        # Persist findings & SLO breach detection (p95/error)
        for f in findings_all:
            db.add(
                Finding(
                    run_id=run_id,
                    severity=f.get("severity", "low"),
                    area=f.get("area", "unknown"),
                    message=f.get("message", ""),
                    trace_id=f.get("trace_id"),
                    suggested_fix=f.get("suggested_fix"),
                )
            )
        # SLO checks
        p95 = None
        err_rate = None
        lk6 = stats_total.get("load_k6") or {}
        p95 = lk6.get("p95_latency_ms")
        err_rate = lk6.get("error_rate")
        if (isinstance(p95, (int, float)) and p95 and p95 > 500.0) or (isinstance(err_rate, (int, float)) and err_rate and err_rate > 0.02):
            db.add(Finding(run_id=run_id, severity="medium", area="load", message=f"SLO breach p95={p95}ms error_rate={err_rate}", trace_id=None, suggested_fix="Investigate recent deploy and rollback if needed"))

        run.stats = stats_total
        run.status = RunStatus.passed if (not findings_all and (stats_total.get("functional", {}).get("failed", 0) == 0)) else RunStatus.failed
        run.finished_at = datetime.now(UTC)
        db.add(run)
        db.commit()

        # Build report
        # Gather findings back
        q_f = db.query(Finding).filter(Finding.run_id == run_id).all()
        run_doc = {
            "id": run.id,
            "suite_id": run.suite_id,
            "status": run.status.value if hasattr(run.status, "value") else str(run.status),
            "stats": run.stats or {},
            "artifacts": run.artifacts or [],
            "target_api_url": run.target_api_url,
            "findings": [
                {
                    "severity": fx.severity.value if hasattr(fx.severity, "value") else str(fx.severity),
                    "area": fx.area,
                    "message": fx.message,
                }
                for fx in q_f
            ],
        }
        html_path = write_html_report(run_id, run_doc)
        pdf_path = try_write_pdf_report(run_id)
        # Emit finished event (best-effort)
        try:
            import asyncio as _asyncio
            from app.interconnect import get_interconnect  # type: ignore
            async def _emit_finish():
                ic = await get_interconnect()
                await ic.publish(stream="events.ops", type="testpack.finished", source="testing_app", data={"run_id": run.id, "status": run.status.value if hasattr(run.status, 'value') else str(run.status), "stats": run.stats or {}})
            _asyncio.get_event_loop().create_task(_emit_finish())
        except Exception:
            pass
        # Teardown chaos if active
        try:
            if chaos_handle is not None:
                stop_experiment(chaos_handle)
        except Exception:
            pass
        return {"status": run_doc["status"], "html": html_path, "pdf": pdf_path}
    finally:
        db.close()


