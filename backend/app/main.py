from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .api import api_router
from .db.init_db import init_db
from .db.session import get_session
from .api.auth import get_current_user
from .db.models import AuditLog
from .core.security.rate_limit import sliding_window_allow
from .core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    try:
        init_db()
    except (ImportError, ValueError, RuntimeError, SQLAlchemyError) as e:
        # Log error but don't fail startup - database might not be available yet
        print(f"Warning: Database initialization failed: {e}")

    yield

    # Shutdown
    pass


app = FastAPI(title="Forge 1 Backend", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router with version prefix
app.include_router(api_router, prefix="/api/v1")


# Basic audit logging + sliding-window rate limiting middleware
@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    response: Response
    try:
        # Sliding-window rate limit by API key (Bearer token) and route
        auth_header = request.headers.get("Authorization", "")
        api_key = auth_header.split(" ", 1)[1] if auth_header.startswith("Bearer ") else None
        if api_key:
            try:
                allowed = sliding_window_allow(
                    settings.redis_url,
                    key=f"rl:sw:{request.url.path}:{api_key}",
                    limit=120,
                    window_seconds=60,
                )
            except Exception:
                allowed = True
            if not allowed:
                # Too many requests, but still log below after building response
                from fastapi.responses import JSONResponse

                resp = JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
                response = resp
                status_code = 429
                raise Exception("rate_limited")
        response = await call_next(request)
        status_code = response.status_code
    except Exception:  # noqa: BLE001
        # If an exception bubbles, mark as 500
        if "status_code" not in locals():
            status_code = 500
        # continue to finally to log
    finally:
        try:
            # Best effort: open a short session and insert an audit row
            # Avoid importing FastAPI dependencies here to prevent dependency cycle
            for session in get_session():
                db = session
                user_ctx: dict[str, str] | None = None
                # We cannot run FastAPI dependencies here; parse header minimally
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    # Attempt to decode for tenant and user id
                    from .api.auth import decode_access_token

                    token = auth_header.split(" ", 1)[1]
                    try:
                        payload = decode_access_token(token)
                        user_ctx = {
                            "user_id": str(payload.get("sub", "")),
                            "tenant_id": str(payload.get("tenant_id", "")),
                        }
                    except Exception:  # noqa: BLE001
                        user_ctx = None

                # Redact sensitive query parameters
                def _redact(val: str) -> str:
                    return "***" if isinstance(val, str) and len(val) > 0 else ""

                query_params = dict(request.query_params)
                for k in list(query_params.keys()):
                    if k.lower() in {"password", "token", "authorization", "apikey", "api_key", "secret"}:
                        query_params[k] = _redact(query_params[k])

                entry = AuditLog(
                    tenant_id=(user_ctx or {}).get("tenant_id"),
                    user_id=int((user_ctx or {}).get("user_id")) if (user_ctx or {}).get("user_id") else None,
                    action="http_request",
                    method=request.method,
                    path=str(request.url.path),
                    status_code=status_code,
                    meta={
                        "query": query_params,
                        "client_ip": getattr(request.client, "host", None),
                    },
                )
                db.add(entry)
                db.commit()
                break
        except Exception:
            # best-effort only
            pass
    return response
