from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.suites import router as suites_router
from app.db.session import engine
from app.models import Base
from testing_app.api import api_router as testing_api_router
from testing_app.db.session import engine as t_engine, ensure_schema as t_ensure_schema
from testing_app.models import Base as TBase
from testing_app.core.config import BASE_ARTIFACTS_DIR


def create_app() -> FastAPI:
    app = FastAPI(title="Forge 1 Testing App", version="0.1.0")

    # Ensure tables exist (including in-memory SQLite for tests)
    Base.metadata.create_all(bind=engine)
    # Create testing schema/tables for the new testing_app APIs
    # Always create testing schema/tables early for in-memory SQLite
    t_ensure_schema()
    TBase.metadata.create_all(bind=t_engine)

    # Routers
    app.include_router(health_router)
    app.include_router(suites_router)
    app.include_router(testing_api_router)

    # CORS (open in dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve artifacts if present
    try:
        app.mount("/artifacts", StaticFiles(directory=str(BASE_ARTIFACTS_DIR), html=False), name="artifacts")
    except Exception:
        pass

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "testing-app"}

    return app


app = create_app()
