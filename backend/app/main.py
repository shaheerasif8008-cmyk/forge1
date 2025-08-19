from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import time
import logging

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .api import api_router
from .api.employees_invoke import router as employees_invoke_router
from .core.config import settings
from .router.runtime import choose_region_for_request, forward_request_to_region
from .core.logging_config import (
    configure_logging,
    generate_trace_id,
    set_request_context,
    clear_request_context,
    get_trace_id,
)
from .core.security.rate_limit import sliding_window_allow
from .db.init_db import init_db
from sqlalchemy import create_engine, text as _sql_text
from redis import Redis
from alembic.config import Config as _AlembicConfig
from alembic.script import ScriptDirectory as _ScriptDirectory
from alembic.runtime.environment import EnvironmentContext as _EnvCtx
from .core.telemetry.prom_metrics import observe_request
from .db.models import AuditLog
from .db.session import get_session
from .core.security.employee_keys import authenticate_employee_key
from .interconnect import get_interconnect
from .interconnect.workers import (
    start_orchestrator_rpc_server,
    start_central_ai_worker,
    start_testing_ai_worker,
    start_ceo_ai_worker,
)
from .core.sandbox import start_sandbox_cleanup_worker
from .proactivity.scheduler import start_scheduler, shutdown_scheduler


# Configure structured logging as early as possible
configure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    try:
        init_db()
    except (ImportError, ValueError, RuntimeError, SQLAlchemyError) as e:
        # In non-dev, fail fast to surface startup issues to the platform orchestrator
        if settings.env != "dev":
            logger.error("Database initialization failed during startup", exc_info=e)
            raise
        # In dev, log and continue for DX
        logger.warning("Database initialization failed during startup", exc_info=e)

    # Initialize interconnect early if enabled
    try:
        if settings.interconnect_enabled:
            import asyncio as _asyncio
            ic = await get_interconnect()
            # Start background workers (non-blocking). In production this can be split into separate processes.
            stop_event = _asyncio.Event()
            _asyncio.create_task(start_orchestrator_rpc_server(ic, stop_event=stop_event))
            _asyncio.create_task(start_central_ai_worker(ic, stop_event=stop_event))
            _asyncio.create_task(start_testing_ai_worker(ic, stop_event=stop_event))
            _asyncio.create_task(start_ceo_ai_worker(ic, stop_event=stop_event))
            _asyncio.create_task(start_sandbox_cleanup_worker(stop_event=stop_event, interval_seconds=60))
    except Exception:
        # Do not block startup in dev/CI
        pass
    # Start proactivity scheduler if enabled
    try:
        if settings.proactivity_enabled:
            start_scheduler()
    except Exception:
        pass

    # Log safe config summary for diagnostics (avoid secrets)
    try:
        logger.info(
            "Config summary",
            extra={
                "event": "config_summary",
                "env": settings.env,
                "db": (settings.database_url.split("@")[-1] if settings.database_url else ""),
                "redis": settings.redis_url,
                "cors": settings.backend_cors_origins,
                "log_level": settings.log_level,
            },
        )
    except Exception:
        pass

    # Non-blocking health checks at startup
    try:
        # DB
        try:
            eng = create_engine(settings.database_url, pool_pre_ping=True, future=True)
            with eng.connect() as conn:
                conn.execute(_sql_text("SELECT 1"))
            logger.info("Startup DB check ok", extra={"event": "startup_check", "db": True})
        except Exception as e:  # noqa: BLE001
            logger.error("Startup DB check failed", exc_info=e, extra={"event": "startup_check", "db": False})
        # Redis
        try:
            r = Redis.from_url(settings.redis_url, decode_responses=True)
            _ = r.ping()
            r.close()
            logger.info("Startup Redis check ok", extra={"event": "startup_check", "redis": True})
        except Exception as e:  # noqa: BLE001
            logger.error("Startup Redis check failed", exc_info=e, extra={"event": "startup_check", "redis": False})
        # Migrations at head
        try:
            cfg = _AlembicConfig("alembic.ini")
            script = _ScriptDirectory.from_config(cfg)
            from alembic.runtime.migration import MigrationContext as _MigCtx
            eng = create_engine(settings.database_url, pool_pre_ping=True, future=True)
            with eng.connect() as conn:
                ctx = _MigCtx.configure(conn)
                current = ctx.get_current_revision()
            heads = set(script.get_heads())
            ok = (current in heads) if heads else True
            logger.info("Startup migrations check", extra={"event": "startup_check", "migrations": ok, "current_rev": current, "heads": list(heads)})
        except Exception as e:  # noqa: BLE001
            logger.error("Startup migrations check failed", exc_info=e, extra={"event": "startup_check", "migrations": False})
    except Exception:
        pass

    yield

    # Shutdown
    try:
        shutdown_scheduler()
    except Exception:
        pass


app = FastAPI(title="Forge 1 Backend", lifespan=lifespan)

# Add CORS middleware
origins_cfg = settings.backend_cors_origins
if settings.env not in {"dev", "local"}:
    if not origins_cfg or origins_cfg.strip() == "*":
        raise RuntimeError("BACKEND_CORS_ORIGINS must be set to specific origins in non-dev environments")
    allow_origins = [o.strip() for o in origins_cfg.split(",") if o.strip()]
else:
    allow_origins = ["*"]

# Fail-fast on missing JWT and loose CORS in non-dev/local
if settings.env not in {"dev", "local"}:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET must be set in non-dev environments")
    if settings.backend_cors_origins.strip() == "*":
        raise RuntimeError("BACKEND_CORS_ORIGINS must not be '*' in non-dev")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional Sentry init (off by default). Only initializes if SENTRY_DSN set and package available.
try:
    import os
    dsn = os.getenv("SENTRY_DSN")
    if dsn:
        import sentry_sdk  # type: ignore
        sentry_sdk.init(dsn=dsn, traces_sample_rate=float(os.getenv("SENTRY_TRACES_RATE", "0")))
except Exception:
    pass

# Mount API router with version prefix
app.include_router(api_router, prefix="/api/v1")

# Also expose the public EaaS invoke API at top-level /v1/employees
app.include_router(employees_invoke_router)

# Prometheus metrics endpoint (public in dev/local; require admin JWT in other envs)
try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest  # type: ignore
    from .api.auth import decode_access_token

    @app.get("/metrics")
    async def metrics_endpoint(request: Request) -> Response | dict[str, str]:  # type: ignore[override]
        # Gate in non-dev/local environments
        if settings.env not in {"dev", "local"}:
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return Response(status_code=401)
            try:
                payload = decode_access_token(auth.split(" ", 1)[1])
                roles = payload.get("roles", [])
                if isinstance(roles, str):
                    roles = [roles]
                if "admin" not in set(roles or []):
                    return Response(status_code=403)
            except Exception:
                return Response(status_code=401)
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
except Exception:
    @app.get("/metrics")
    async def metrics_unavailable() -> dict[str, str]:  # type: ignore[override]
        return {"status": "metrics_unavailable"}


@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    start_ts = time.time()
    response: Response | None = None
    status_code = 500
    # Extract or create a trace ID and parse minimal auth for tenant/user
    trace_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    if not trace_id:
        trace_id = generate_trace_id()

    tenant_id = ""
    user_id = ""
    principal: str | None = None
    auth_header = request.headers.get("Authorization", "")
    api_key = auth_header.split(" ", 1)[1] if auth_header.startswith("Bearer ") else None
    if api_key:
        try:
            from .api.auth import decode_access_token

            payload = decode_access_token(api_key)
            tenant_id = str(payload.get("tenant_id", ""))
            user_id = str(payload.get("sub", ""))
            principal = f"user:{user_id}" if user_id else None
        except Exception:  # noqa: BLE001
            pass

    # Fallback: Employee-Key header based auth
    if not principal:
        emp_hdr = request.headers.get("Employee-Key")
        try:
            # Create a one-off DB session to validate the key without conflicting with per-route sessions
            for session in get_session():
                db = session
                ek = authenticate_employee_key(emp_hdr, db=db, pepper=settings.employee_key_pepper)
                if ek is not None:
                    tenant_id = ek.tenant_id
                    principal = f"employee_key:{ek.employee_key_id}"
                break
        except Exception:  # noqa: BLE001
            pass

    # Set logging context
    set_request_context(
        trace_id=trace_id,
        tenant_id=tenant_id or None,
        user_id=user_id or None,
        method=request.method,
        path=str(request.url.path),
    )

    # Rate limit per tenant/user/route when available
    try:
        if api_key or principal:
            try:
                allowed = sliding_window_allow(
                    settings.redis_url,
                    key=f"rl:sw:{request.url.path}:{tenant_id or 'anon'}:{(user_id or principal or 'anon')}",
                    limit=120,
                    window_seconds=60,
                )
            except Exception:
                allowed = True
            if not allowed:
                from fastapi.responses import JSONResponse

                response = JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
                status_code = 429
                logger.warning("Rate limit exceeded", extra={"event": "rate_limit"})
                raise Exception("rate_limited")

        logger.info("Request start")
        # Multi-region cost-based routing: forward non-critical paths to cheaper healthy regions
        forwarded = False
        try:
            if settings.multi_region_routing_enabled:
                region = await choose_region_for_request(str(request.url.path))
                if region and settings.region and region != settings.region:
                    body = None
                    try:
                        body = await request.json()
                    except Exception:
                        body = None
                    status_code, payload = await forward_request_to_region(
                        region,
                        request.method,
                        str(request.url.path),
                        headers={"content-type": request.headers.get("content-type", "application/json")},
                        json_body=body,
                    )
                    from fastapi.responses import JSONResponse
                    if isinstance(payload, (dict, list)):
                        response = JSONResponse(status_code=status_code, content=payload)
                    else:
                        response = Response(status_code=status_code, content=str(payload))
                    forwarded = True
        except Exception:
            forwarded = False
        if not forwarded:
            response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:  # noqa: BLE001
        # Log the exception with stack
        logger.exception("Unhandled request error", exc_info=exc)
        if response is None:
            from fastapi.responses import JSONResponse
            # In dev/local, include traceback for DX; in other envs, keep terse
            if settings.env in {"dev", "local"}:
                import traceback
                response = JSONResponse({"detail": str(exc), "trace": traceback.format_exc()}, status_code=500)
            else:
                response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)
            status_code = 500
    finally:
        # Add trace id header for clients
        if response is not None:
            try:
                response.headers["X-Trace-ID"] = trace_id
            except Exception:  # noqa: BLE001
                pass

        # Persist audit log (best-effort)
        try:
            for session in get_session():
                db = session
                # Redact sensitive query parameters
                def _redact(val: str) -> str:
                    return "***" if isinstance(val, str) and len(val) > 0 else ""

                query_params = dict(request.query_params)
                for k in list(query_params.keys()):
                    if k.lower() in {"password", "token", "authorization", "apikey", "api_key", "secret"}:
                        query_params[k] = _redact(query_params[k])

                entry = AuditLog(
                    tenant_id=tenant_id or None,
                    user_id=int(user_id) if user_id.isdigit() else None,
                    action="http_request",
                    method=request.method,
                    path=str(request.url.path),
                    status_code=status_code,
                    meta={
                        "query": query_params,
                        "client_ip": getattr(request.client, "host", None),
                        "trace_id": trace_id,
                        "duration_ms": int((time.time() - start_ts) * 1000),
                    },
                )
                db.add(entry)
                db.commit()
                try:
                    observe_request(
                        route=str(request.url.path),
                        method=request.method,
                        status_code=status_code,
                        duration_seconds=max(0.0, (time.time() - start_ts)),
                    )
                except Exception:
                    pass
                break
        except Exception:  # noqa: BLE001
            pass

        # Log the end of request
        logger.info("Request end")
        # Clear logging context at end of request
        clear_request_context()

    return response


# ---- OpenAPI customization: document auth headers and error shape ----

class ErrorResponse(BaseModel):
    detail: str


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="Forge 1 API",
        routes=app.routes,
    )
    components = openapi_schema.setdefault("components", {})
    # Security schemes
    sec = components.setdefault("securitySchemes", {})
    # JWT bearer (already implied by OAuth2PasswordBearer but we add explicit header auth for clarity)
    sec.setdefault(
        "BearerAuth",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token in Authorization: Bearer <token>",
        },
    )
    # Employee-Key header for EaaS
    sec.setdefault(
        "EmployeeKey",
        {
            "type": "apiKey",
            "in": "header",
            "name": "Employee-Key",
            "description": "Employee API key header: EK_<prefix>.<secret>",
        },
    )
    # Error shape schema
    schemas = components.setdefault("schemas", {})
    if "ErrorResponse" not in schemas:
        schemas["ErrorResponse"] = {
            "title": "ErrorResponse",
            "type": "object",
            "properties": {"detail": {"type": "string"}},
            "required": ["detail"],
        }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[assignment]
