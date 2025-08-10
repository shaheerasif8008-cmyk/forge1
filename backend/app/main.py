from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routers.auth import router as auth_router
from .routers.health import router as health_router
from .services.database import close_db_pool, create_db_pool
from .services.redis_client import close_redis_client, create_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_redis_client(settings.redis_url)
    await create_db_pool(settings.database_url)
    yield
    await close_redis_client()
    await close_db_pool()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.backend_cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = FastAPI()
api.include_router(auth_router)
api.include_router(health_router)

app.mount(settings.api_v1_prefix, api)


