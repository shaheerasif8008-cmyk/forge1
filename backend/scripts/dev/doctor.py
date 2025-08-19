#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import json
import socket
from contextlib import closing
from typing import Any

from sqlalchemy import create_engine, text
from redis import Redis


def getenv(name: str, default: str | None = None) -> str:
    val = os.getenv(name)
    return val if val is not None else (default or "")


def check_db(url: str) -> tuple[bool, str]:
    try:
        eng = create_engine(url, pool_pre_ping=True, future=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def check_redis(url: str) -> tuple[bool, str]:
    try:
        r = Redis.from_url(url, decode_responses=True, socket_connect_timeout=1.0, socket_timeout=1.0)
        ok = bool(r.ping())
        r.close()
        return ok, "ok" if ok else "ping false"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def check_migrations_at_head() -> tuple[bool, str]:
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.environment import EnvironmentContext
        cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
        script = ScriptDirectory.from_config(cfg)
        def _cmp(rev, context):
            return set(script.get_heads()) == (set([rev]) if rev else set())
        ok = bool(EnvironmentContext(cfg, script, fn=_cmp).run_migrations())
        return ok, "ok" if ok else f"current != head ({','.join(script.get_heads())})"
    except Exception as e:
        return False, str(e)


def _host_port_from_url(url: str) -> str:
    try:
        # crude parse: scheme://user:pass@host:port/db
        tail = url.split("@")[-1]
        host_port_db = tail.split("/")[0]
        return host_port_db
    except Exception:
        return url


def main() -> int:
    # Load env (pydantic already supports .env in app, but ensure we read for script too)
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=False)

    env = getenv("ENV", "local")
    db_url = getenv("DATABASE_URL", "")
    redis_url = getenv("REDIS_URL", "")

    result: dict[str, Any] = {
        "env": env,
        "db": {"url": _host_port_from_url(db_url) if db_url else "unset"},
        "redis": {"url": redis_url or "unset"},
    }

    ok_db, msg_db = check_db(db_url) if db_url else (False, "DATABASE_URL unset")
    ok_redis, msg_redis = check_redis(redis_url) if redis_url else (False, "REDIS_URL unset")
    ok_mig, msg_mig = check_migrations_at_head()

    result["checks"] = {
        "db": {"ok": ok_db, "detail": msg_db},
        "redis": {"ok": ok_redis, "detail": msg_redis},
        "migrations": {"ok": ok_mig, "detail": msg_mig},
    }

    print(json.dumps(result, indent=2))
    # Guidance
    if not ok_db:
        print("\n[doctor] DB check failed. Ensure local Postgres is running and DATABASE_URL is set.", file=sys.stderr)
        print("[doctor] For local: postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local", file=sys.stderr)
        print("[doctor] Try: docker compose -f docker-compose.local.yml up -d", file=sys.stderr)
    if not ok_redis:
        print("\n[doctor] Redis check failed. Ensure Redis is running and REDIS_URL is set.", file=sys.stderr)
        print("[doctor] For local: redis://127.0.0.1:6382/0", file=sys.stderr)
    if not ok_mig:
        print("\n[doctor] Migrations not at head. Run: alembic upgrade head (or scripts/migrate_local.sh)", file=sys.stderr)
    return 0 if (ok_db and ok_redis and ok_mig) else 2


if __name__ == "__main__":
    sys.exit(main())


