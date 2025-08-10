from typing import Any

from fastapi import APIRouter, Depends, Response, status
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.session import get_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/ready")
async def ready(response: Response, db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
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

    if not (db_ok and redis_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "postgres": db_ok, "redis": redis_ok}
    return {"status": "ready"}


