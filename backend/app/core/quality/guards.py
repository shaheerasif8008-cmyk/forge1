from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ..config import settings
import os
from ...db.session import SessionLocal
from ...db.models import Employee
from ...interconnect import get_interconnect

try:
    from redis import Redis
except Exception:  # pragma: no cover - optional at runtime
    Redis = None  # type: ignore

_inmem_store: dict[str, int] = {}
_inmem_idem: dict[str, tuple[int, str]] = {}

# Strict tool allowlist for internal AIs
ALLOWED_INTERNAL_TOOLS = {
    "run_testpack",
    "compare_metrics",
    "open_pr",
    "promote_release",
    "rollback_release",
}


def _redis() -> Any | None:
    try:
        if Redis is None:
            return None
        return Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


def clamp_tokens(requested: int | None) -> int:
    max_allowed = int(getattr(settings, "max_tokens_per_req", 2048))
    if requested is None or requested <= 0:
        return max_allowed
    return min(int(requested), max_allowed)


def _employee_daily_cap(employee_id: str | None) -> int | None:
    # Look up per-employee cap from DB config if present; else use default
    try:
        if not employee_id:
            return None
        with SessionLocal() as db:
            emp = db.get(Employee, employee_id)
            if emp and isinstance(emp.config, dict):
                cap = emp.config.get("daily_tokens_cap")
                if cap is not None:
                    return int(cap)
    except Exception:
        pass
    # fallback default (support dynamic env override for tests)
    env_cap = os.getenv("EMPLOYEE_DAILY_TOKENS_CAP")
    if env_cap is not None:
        try:
            return int(env_cap)
        except Exception:
            return None
    default_cap = getattr(settings, "employee_daily_tokens_cap", None)
    return int(default_cap) if default_cap is not None else None


def _daily_key(prefix: str, ident: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}:{ident}:{day}"


def check_and_reserve_tokens(tenant_id: str | None, employee_id: str | None, tokens: int) -> bool:
    """Reserve tokens for this request against a daily cap.

    Returns True when allowed; False if cap would be exceeded.
    """
    if tokens <= 0:
        return True
    # Check tenant cap first (if configured)
    tenant_key = _daily_key("budget:tokens:tenant", tenant_id) if tenant_id else None
    employee_key = _daily_key("budget:tokens:employee", employee_id) if employee_id else None
    # Tenant cap via env (optional)
    tenant_cap_env = os.getenv("TENANT_DAILY_TOKENS_CAP")
    tenant_cap = int(tenant_cap_env) if tenant_cap_env and tenant_cap_env.isdigit() else None
    # Determine cap: explicit employee cap first; otherwise global default cap
    emp_cap = _employee_daily_cap(employee_id)
    if emp_cap is None:
        emp_cap = _employee_daily_cap("__global__")
    r = _redis()
    try:
        if r is not None:
            pipe = r.pipeline()
            # Reserve tenant budget if applicable
            if tenant_key:
                pipe.incrby(tenant_key, tokens)
                pipe.expire(tenant_key, 2 * 24 * 3600, nx=True)
            if employee_key:
                pipe.incrby(employee_key, tokens)
                pipe.expire(employee_key, 2 * 24 * 3600, nx=True)
            results = pipe.execute()
            # Evaluate caps
            idx = 0
            if tenant_key:
                tenant_current = int(results[idx]); idx += 2
            if tenant_cap is not None and tenant_current is not None and tenant_current > tenant_cap:
                    # Roll back tenant inc
                    try:
                        r.decrby(tenant_key, tokens)
                    except Exception:
                        pass
                    return False
            emp_current = None
            if employee_key:
                emp_current = int(results[idx]); idx += 2
            if emp_cap is not None and emp_current is not None and emp_current > emp_cap:
                # Roll back reservation by decrementing
                try:
                    if employee_key:
                        r.decrby(employee_key, tokens)
                    if tenant_key:
                        r.decrby(tenant_key, tokens)
                except Exception:
                    pass
                # Emit budget.exceeded event (best-effort)
                try:
                    import asyncio as _asyncio
                    async def _emit():
                        ic = await get_interconnect()
                        await ic.publish(
                            stream="events.ops",
                            type="budget.exceeded",
                            source="budget_guard",
                            tenant_id=tenant_id or "unknown",
                            employee_id=employee_id,
                            data={"cap": emp_cap, "requested": tokens},
                        )
                    _asyncio.create_task(_emit())
                except Exception:
                    pass
                return False
            return True
    except Exception:
        pass
    # In-memory fallback
    if tenant_key:
        _inmem_store[tenant_key] = _inmem_store.get(tenant_key, 0) + tokens
        if tenant_cap is not None and _inmem_store[tenant_key] > tenant_cap:
            _inmem_store[tenant_key] -= tokens
            return False
    # Track employee/global usage even when no employee_id via a synthetic key
    emp_track_key = employee_key or "budget:tokens:employee:__global__"
    current = _inmem_store.get(emp_track_key, 0) + tokens
    if emp_cap is not None and current > emp_cap:
        if tenant_key:
            _inmem_store[tenant_key] = max(0, _inmem_store.get(tenant_key, 0) - tokens)
        return False
    _inmem_store[emp_track_key] = current
    return True


def enforce_tool_allowlist(tool_name: str) -> bool:
    """Return True if the tool is allowed for internal AIs."""
    return tool_name in ALLOWED_INTERNAL_TOOLS


def idempotency_check_and_store(*, tenant_id: str | None, key: str | None, request_fingerprint: str, ttl_seconds: int = 24 * 3600) -> tuple[bool, str | None]:
    """Idempotency helper for write endpoints.

    Returns (is_duplicate, stored_response_key). If duplicate and response key present,
    the caller can fetch a cached response by that key to return immediately.
    """
    if not key:
        return (False, None)
    now = int(time.time())
    r = _redis()
    redis_key = f"idem:{tenant_id or 'global'}:{key}"
    try:
        if r is not None:
            prev = r.hget(redis_key, "fp")
            if prev is not None and str(prev) == request_fingerprint:
                resp_key = r.hget(redis_key, "resp_key")
                return (True, str(resp_key) if resp_key else None)
            pipe = r.pipeline()
            pipe.hset(redis_key, mapping={"fp": request_fingerprint, "ts": str(now)})
            pipe.expire(redis_key, ttl_seconds, nx=True)
            pipe.execute()
            return (False, None)
    except Exception:
        pass
    # In-memory fallback (process-scoped)
    prev = _inmem_idem.get(redis_key)
    if prev and prev[1] == request_fingerprint:
        return (True, None)
    _inmem_idem[redis_key] = (now, request_fingerprint)
    return (False, None)


def idempotency_store_response(*, tenant_id: str | None, key: str | None, response_payload: dict[str, Any], ttl_seconds: int = 24 * 3600) -> None:
    if not key:
        return
    r = _redis()
    store_key = f"idemr:{tenant_id or 'global'}:{key}"
    try:
        if r is not None:
            import json as _json
            r.setex(store_key, ttl_seconds, _json.dumps(response_payload))
            r.hset(f"idem:{tenant_id or 'global'}:{key}", "resp_key", store_key)
            return
    except Exception:
        pass
    # best-effort fallback marker
    _inmem_store[store_key] = 1


