from fastapi import APIRouter

from .ai import router as ai_router
from .auth import router as auth_router
from .employees import router as employees_router
from .health import router as health_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(employees_router)
api_router.include_router(ai_router)
