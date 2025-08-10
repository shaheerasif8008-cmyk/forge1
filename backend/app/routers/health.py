from fastapi import APIRouter

from ..services.database import get_db_pool
from ..services.redis_client import get_redis_client


router = APIRouter()


@router.get("/health", summary="Health check")
async def health() -> dict:
    db_ok = False
    redis_ok = False

    try:
        pool = get_db_pool()
        async with pool.connection() as conn:
            await conn.execute("SELECT 1;")
        db_ok = True
    except Exception:
        db_ok = False

    try:
        redis = await get_redis_client()
        pong = await redis.ping()
        redis_ok = bool(pong)
    except Exception:
        redis_ok = False

    return {"status": "ok" if db_ok and redis_ok else "degraded", "postgres": db_ok, "redis": redis_ok}


