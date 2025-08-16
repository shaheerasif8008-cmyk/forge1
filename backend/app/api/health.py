from typing import Any

from fastapi import APIRouter, Depends, Response, status
import logging
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.session import get_session
from ..core.logging_config import get_trace_id

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/ready")
async def ready(
    response: Response, db: Session = Depends(get_session)  # noqa: B008
) -> dict[str, Any]:
    db_ok = False
    redis_ok = False

    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False

    try:
        sync_client: Any = Redis.from_url(settings.redis_url, decode_responses=True)
        redis_ok = bool(sync_client.ping())
        sync_client.close()
    except Exception:  # noqa: BLE001
        redis_ok = False

    # Degraded-ready: if DB is down but Redis is up, return 200 with degraded flag in dev only.
    if db_ok and redis_ok:
        return {"status": "ready", "trace_id": get_trace_id()}
    # In dev/local, allow degraded state to be considered ready for basic UI/dev flows
    from ..core.config import settings as cfg
    if cfg.env in {"dev", "local"} and redis_ok:
        return {"status": "ready_degraded", "postgres": db_ok, "redis": redis_ok, "trace_id": get_trace_id()}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "unready", "postgres": db_ok, "redis": redis_ok, "trace_id": get_trace_id()}


@router.get("/")
async def health(db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    """Health check endpoint that matches frontend expectations."""
    postgres_ok = True
    redis_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        postgres_ok = False
    try:
        client: Any = Redis.from_url(settings.redis_url, decode_responses=True)
        redis_ok = bool(client.ping())
        client.close()
    except Exception:  # noqa: BLE001
        redis_ok = False
    return {
        "status": "healthy" if (postgres_ok and redis_ok) else "unhealthy",
        "postgres": postgres_ok,
        "redis": redis_ok,
        "trace_id": get_trace_id(),
    }
