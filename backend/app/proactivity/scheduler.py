from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

try:
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
except Exception:  # pragma: no cover - optional dep in tests
    BackgroundScheduler = None  # type: ignore[assignment]

from ..core.config import settings
from ..db.session import SessionLocal
from ..db.models import Employee, TaskExecution
from ..core.telemetry.metrics_service import MetricsService

logger = logging.getLogger(__name__)


@dataclass
class InboxItem:
    source: str  # email|slack
    subject: str
    body: str
    received_at: datetime


def _mock_inbox(now: datetime) -> list[InboxItem]:
    # Deterministic mock: one message every run for demo
    return [
        InboxItem(
            source="email",
            subject="Weekly report request",
            body="Please summarize last week's activity",
            received_at=now,
        )
    ]


def _scan_and_act() -> None:
    now = datetime.now(UTC)
    runs = 0
    alerts = 0
    with SessionLocal() as db:
        # No runtime DDL here; assume migrations have been applied
        # Overdue tasks: find failed or long running in last day and alert
        day_ago = now - timedelta(days=1)
        try:
            overdue = (
                db.query(TaskExecution)
                .filter(TaskExecution.created_at >= day_ago)
                .filter((TaskExecution.success.is_(False)) | (TaskExecution.execution_time.isnot(None) & (TaskExecution.execution_time > 60_000)))
                .limit(20)
                .all()
            )
        except Exception:
            overdue = []
        if overdue:
            alerts += len(overdue)
            _send_mock_alert(f"{len(overdue)} overdue tasks detected")

        # Mock inbox → create tasks on first employee if any exist
        try:
            employees = db.query(Employee).limit(1).all()
        except Exception:
            db.rollback()
            employees = []
        inbox = _mock_inbox(now)
        if employees and inbox:
            emp = employees[0]
            # For demo: create a log entry to simulate auto task creation
            db.add(
                TaskExecution(
                    tenant_id=emp.tenant_id,
                    employee_id=emp.id,
                    user_id=0,
                    task_type="proactive:auto",
                    prompt=inbox[0].subject,
                    response="auto-created",
                    model_used="proactive",
                    tokens_used=0,
                    execution_time=10,
                    success=True,
                    error_message=None,
                    cost_cents=0,
                    task_data="{}",
                )
            )
            db.commit()
            runs += 1
    try:
        ms = MetricsService()
        # Record one scheduler run and alerts count via actor/run metrics
        if runs:
            ms.incr_actor_run("proactivity_run")
        if alerts:
            ms.incr_actor_run("proactivity_alert")
    except Exception:
        pass
    logger.info("Proactivity scan completed", extra={"runs": runs, "alerts": alerts})


def _send_mock_alert(message: str) -> None:
    """Send a mock alert via dev Slack/email adapters (logs in local/dev)."""
    try:
        _send_dev_slack(message)
    except Exception:
        pass
    try:
        _send_dev_email("Proactivity Alert", message)
    except Exception:
        pass
    # Avoid clobbering logging's reserved 'message' field
    logger.warning("Proactivity alert", extra={"alert_message": message})


def _send_dev_slack(text: str) -> None:
    url = os.getenv("DEV_SLACK_WEBHOOK_URL")
    if not url:
        logger.debug("DEV_SLACK_WEBHOOK_URL not set; skipping Slack alert")
        return
    try:
        import json, urllib.request
        req = urllib.request.Request(url, data=json.dumps({"text": text}).encode("utf-8"), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        logger.debug("Slack mock send failed; ignored in dev")


def _send_dev_email(subject: str, body: str) -> None:
    to_addr = os.getenv("DEV_EMAIL_TO")
    if not to_addr:
        logger.debug("DEV_EMAIL_TO not set; skipping email alert")
        return
    # In dev, just write to logs; real email adapter would integrate with mail provider
    logger.info("Mock email", extra={"to": to_addr, "subject": subject, "body": body})


_scheduler: Any | None = None


def start_scheduler() -> None:
    global _scheduler
    # Optional dependency: only start if available
    if BackgroundScheduler is None:
        logger.info("APScheduler not installed; skipping proactivity scheduler")
        return
    if not settings.proactivity_enabled:
        logger.info("Proactivity disabled by config")
        return
    period = max(30, int(os.getenv("SCHEDULE_PERIOD_SEC", str(settings.schedule_period_sec)) or 300))
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(_scan_and_act, "interval", seconds=period, id="proactivity_scan", replace_existing=True, next_run_time=datetime.now(UTC))
        _scheduler.start()
        logger.info("Proactivity scheduler started", extra={"period_sec": period})


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None


