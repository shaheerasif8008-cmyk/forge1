from __future__ import annotations

import asyncio
import logging
from typing import Any

from redis import Redis

from ..core.config import settings
from ..core.runtime.deployment_runtime import DeploymentRuntime
from ..db.models import Employee
from ..db.session import SessionLocal
from .sdk import Interconnect
from .redis_streams import RetryPolicy
from .cloudevents import CloudEvent

logger = logging.getLogger(__name__)


async def start_orchestrator_rpc_server(ic: Interconnect, stop_event: asyncio.Event | None = None) -> None:
    async def dry_run_handler(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            params = payload.get("params", {})
            employee_id = str(params.get("employee_id", ""))
            seed = str(params.get("seed", "Hello from dry_run"))
            if not employee_id:
                return {"ok": False, "error": "missing_employee_id"}
            with SessionLocal() as db:
                emp = db.get(Employee, employee_id)
                if emp is None:
                    return {"ok": False, "error": "employee_not_found"}
                runtime = DeploymentRuntime(employee_config=emp.config)
                ctx = {"tenant_id": emp.tenant_id, "employee_id": emp.id, "dry_run": True}
                results = await runtime.start(seed, iterations=1, context=ctx)
                out = [r.model_dump() for r in results]
                return {"ok": True, "results": out}
        except Exception as e:  # noqa: BLE001
            logger.exception("dry_run handler failed", exc_info=e)
            return {"ok": False, "error": str(e)}

    await ic.rpc_register_and_serve(
        group="orchestrator",
        consumer="svc",
        registrations={"orchestrator.dry_run": dry_run_handler},
        stop_event=stop_event,
    )


async def start_central_ai_worker(ic: Interconnect, stop_event: asyncio.Event | None = None) -> None:
    async def on_event(ev: CloudEvent) -> bool:
        try:
            if ev.type != "employee.created":
                return True
            employee_id = ev.employee_id or (ev.subject or "")
            if not employee_id:
                return True
            # Make RPC call to orchestrator
            res = await ic.rpc_call(
                method="orchestrator.dry_run",
                params={"employee_id": employee_id, "seed": "Introduce yourself briefly."},
                timeout_ms=8000,
                metadata={"tenant_id": ev.tenant_id},
            )
            # Publish results
            await ic.publish(
                stream="events.employees",
                type="employee.dry_run.completed" if (res or {}).get("ok") else "employee.dry_run.failed",
                source="central_ai",
                subject=employee_id,
                tenant_id=ev.tenant_id,
                employee_id=employee_id,
                data={"rpc": res},
            )
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"central_ai worker error: {e}")
            return True

    await ic.subscribe(
        stream="events.employees",
        group="central-ai",
        consumer=f"central-{id(stop_event)}",
        handler=on_event,
        stop_event=stop_event,
        retry=RetryPolicy(max_attempts=3, base_delay_ms=250, max_delay_ms=2000),
    )


async def start_testing_ai_worker(ic: Interconnect, stop_event: asyncio.Event | None = None) -> None:
    r = Redis.from_url(settings.redis_url, decode_responses=True)

    async def on_event(ev: CloudEvent) -> bool:
        if ev.type != "task.failed":
            return True
        tenant = ev.tenant_id or "unknown"
        key = f"spike:tasks_failed:{tenant}"
        try:
            cur = r.incr(key)
            r.expire(key, 60, nx=True)
            threshold = int(getattr(settings, "test_spike_threshold", 5))
            if cur >= threshold:
                # Trigger testpack
                await ic.publish(
                    stream="events.ops",
                    type="testpack.run",
                    source="testing_ai",
                    tenant_id=tenant,
                    data={"reason": "task_failed_spike", "count": cur},
                )
                r.delete(key)
        except Exception:
            pass
        return True

    await ic.subscribe(
        stream="events.tasks",
        group="testing-ai",
        consumer=f"testing-{id(stop_event)}",
        handler=on_event,
        stop_event=stop_event,
        retry=RetryPolicy(max_attempts=3, base_delay_ms=250, max_delay_ms=2000),
    )


async def start_ceo_ai_worker(ic: Interconnect, stop_event: asyncio.Event | None = None) -> None:
    async def on_core(ev: CloudEvent) -> bool:
        try:
            if ev.type == "metrics.task" and isinstance(ev.data, dict):
                tokens = int(ev.data.get("tokens_used", 0) or 0)
                if tokens > 10000:
                    await ic.publish(
                        stream="events.ops",
                        type="ops.proposal",
                        source="ceo_ai",
                        tenant_id=ev.tenant_id,
                        data={"proposal": "reduce_max_tokens", "tokens": tokens},
                    )
        except Exception:
            pass
        return True

    async def on_ops(ev: CloudEvent) -> bool:
        try:
            if ev.type == "budget.exceeded":
                await ic.publish(
                    stream="events.ops",
                    type="ops.proposal",
                    source="ceo_ai",
                    tenant_id=ev.tenant_id,
                    employee_id=ev.employee_id,
                    data={"proposal": "pause_high_cost_tasks"},
                )
        except Exception:
            pass
        return True

    # Run two subscriptions concurrently
    async def _run():
        await asyncio.gather(
            ic.subscribe(
                stream="events.core",
                group="ceo-ai",
                consumer=f"ceo-core-{id(stop_event)}",
                handler=on_core,
                stop_event=stop_event,
            ),
            ic.subscribe(
                stream="events.ops",
                group="ceo-ai",
                consumer=f"ceo-ops-{id(stop_event)}",
                handler=on_ops,
                stop_event=stop_event,
            ),
        )

    await _run()


