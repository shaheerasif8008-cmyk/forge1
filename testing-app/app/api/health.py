from __future__ import annotations

from fastapi import APIRouter

from app.config import settings


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "db": settings.database_url,
        "redis": settings.redis_url,
        "ns": settings.vector_namespace_prefix,
    }
