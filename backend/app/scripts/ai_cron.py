from __future__ import annotations

"""Cron entrypoints for internal AIs (CEO AI, Central AI, Testing AI).

Run via: `python -m app.scripts.ai_cron <actor>` where actor in {ceo_ai, central_ai, testing_ai}
This script is safe to run in dev/CI.
"""

import sys
from datetime import UTC, datetime
from typing import Any

from ..db.session import SessionLocal
from ..db.models import AiInsight, AiRiskReport, DailyUsageMetric, RefinementSlo, RefinementAction, Employee
from ..core.telemetry.metrics_service import MetricsService
from ..interconnect import get_interconnect
from ..core.config import settings


def _record_insight(actor: str, title: str, body: str, labels: dict[str, Any] | None, metrics: dict[str, Any] | None) -> None:
    with SessionLocal() as db:
        row = AiInsight(actor=actor, title=title, body=body, labels=labels or {}, metrics=metrics or {})
        db.add(row)
        db.commit()


def run_ceo_ai() -> None:
    # Minimal useful behavior: synthesize an insight record based on placeholder metrics.
    metrics = {"tasks_24h": 0, "success_ratio": 0.0, "p95_latency_ms": 0}
    _record_insight(
        "ceo_ai",
        "Daily KPI summary",
        "KPIs stable. Recommend A/B test on onboarding variant B.",
        {"growth": True},
        metrics,
    )
    MetricsService().incr_actor_run("ceo_ai")
    # Subscribe to testpack.finished and log greenlight/remediation (best-effort)
    try:
        import asyncio as _asyncio
        async def _watch():
            ic = await get_interconnect()
            async def _handler(ev):
                if ev.type == "testpack.finished":
                    status = str((ev.data or {}).get("status", ""))
                    rid = (ev.data or {}).get("run_id")
                    note = "Greenlight deploy." if status == "pass" else "Investigate/regress deploy."
                    _record_insight("ceo_ai", f"Testpack result: {status}", f"Run {rid}: {note}", {"testpack": True}, {"status": status})
                    return True
                return False
            await ic.subscribe(stream="events.ops", group="ceo_ai", consumer="ceo_ai", handler=_handler)
        _asyncio.get_event_loop().create_task(_watch())
    except Exception:
        pass
    # Example: publish an ops proposal event (best-effort)
    try:
        import asyncio as _asyncio
        async def _emit():
            ic = await get_interconnect()
            await ic.publish(stream="events.ops", type="ops.proposal", source="ceo_ai", data={"action": "optimize_costs"})
        _asyncio.get_event_loop().create_task(_emit())
    except Exception:
        pass


def run_central_ai() -> None:
    # Placeholder: central AI would evaluate employees and propose promotions.
    _record_insight(
        "central_ai",
        "Evaluation cycle",
        "Evaluated new employees; all within baseline latency.",
        {"infra": True},
        {},
    )
    MetricsService().incr_actor_run("central_ai")
    # Placeholder: subscribe to employee.created would be in a worker process


def run_testing_ai() -> None:
    with SessionLocal() as db:
        db.add(AiRiskReport(report={"heatmap": {"prompt_injection": "medium", "cost_overrun": "low"}, "ts": datetime.now(UTC).isoformat()}))
        db.commit()
    _record_insight("testing_ai", "Risk report updated", "See latest risk heatmap.", {"quality": True}, {})
    MetricsService().incr_actor_run("testing_ai")
    # Emit region heartbeat (best-effort, synchronous) so health-based routing has signal
    try:
        import asyncio as _asyncio
        async def _beat():
            ic = await get_interconnect()
            await ic.set_region_health(settings.region or "local", healthy=True, ttl_secs=settings.region_health_ttl_secs)
        _asyncio.get_event_loop().run_until_complete(_beat())
    except Exception:
        pass


def run_refinement_engine() -> None:
    with SessionLocal() as db:
        # Defaults in absence of per-role SLOs
        slo_by_role: dict[str, dict[str, float | int]] = {}
        for s in db.query(RefinementSlo).all():
            slo_by_role[s.role_name or "*"] = {
                "min_success_ratio": float(s.min_success_ratio or 0.7),
                "max_p95_ms": int(s.max_p95_ms or 30000),
                "max_cost_cents": int(s.max_cost_cents or 0),
            }
        employees = db.query(Employee).limit(200).all()
        for emp in employees:
            m = (
                db.query(DailyUsageMetric)
                .filter(
                    DailyUsageMetric.tenant_id == emp.tenant_id,
                    DailyUsageMetric.employee_id == emp.id,
                )
                .order_by(DailyUsageMetric.day.desc())
                .first()
            )
            if not m or not m.tasks:
                continue
            success_ratio = float(m.success_ratio or 0.0)
            p95_ms = float(m.avg_duration_ms or 0.0) * 1.5
            role = (emp.config or {}).get("role", {}).get("name", "*")
            slo = slo_by_role.get(role) or slo_by_role.get("*") or {"min_success_ratio": 0.7, "max_p95_ms": 30000}
            breach = success_ratio < float(slo.get("min_success_ratio", 0.7)) or p95_ms > int(slo.get("max_p95_ms", 30000))
            if not breach:
                continue
            db.add(RefinementAction(employee_id=emp.id, action="proposed", details={"success_ratio": success_ratio, "p95_ms": p95_ms, "slo": slo}))
            db.commit()


if __name__ == "__main__":
    actor = sys.argv[1] if len(sys.argv) > 1 else ""
    if actor == "ceo_ai":
        run_ceo_ai()
    elif actor == "central_ai":
        run_central_ai()
    elif actor == "testing_ai":
        run_testing_ai()
    else:
        print("Usage: python -m app.scripts.ai_cron <ceo_ai|central_ai|testing_ai>")
        raise SystemExit(2)


