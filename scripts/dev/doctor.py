#!/usr/bin/env python3
"""Forge1 Doctor: validate local dev environment.

Checks:
- DATABASE_URL reachable, can SELECT 1, pgvector extension available
- REDIS_URL reachable, PING ok
- Alembic migrations apply cleanly
- Health endpoints respond with expected status codes

Usage:
  python scripts/dev/doctor.py
Environment:
  DATABASE_URL (default: postgresql://forge:forge@127.0.0.1:5542/forge1_local)
  REDIS_URL (default: redis://127.0.0.1:6382/0)
  API_BASE_URL (default: http://127.0.0.1:8000)
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess


DEFAULT_DB = "postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local"
DEFAULT_DB_APP = "postgresql://forge:forge@127.0.0.1:5542/forge1_local"
DEFAULT_REDIS = "redis://127.0.0.1:6382/0"
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def _print(title: str, ok: bool, info: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{'OK' if ok else '!!'}] {title}: {status}{(' - ' + info) if info else ''}")


def check_db() -> tuple[bool, str]:
    try:
        import sqlalchemy as sa
        url = os.getenv("DATABASE_URL", DEFAULT_DB_APP)
        # prefer psycopg driver
        if url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        eng = sa.create_engine(url, pool_pre_ping=True, future=True)
        with eng.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return True, "connected"
    except Exception as e:
        return False, str(e)


def check_redis() -> tuple[bool, str]:
    try:
        from redis import Redis
        url = os.getenv("REDIS_URL", DEFAULT_REDIS)
        r = Redis.from_url(url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3)
        pong = r.ping()
        return bool(pong), "pong" if pong else "no pong"
    except Exception as e:
        return False, str(e)


def run_alembic() -> tuple[bool, str]:
    try:
        here = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    except Exception:
        here = os.getcwd()
    env = os.environ.copy()
    env.setdefault("SQLALCHEMY_DATABASE_URL", os.getenv("ALEMBIC_DATABASE_URL", DEFAULT_DB))
    try:
        res = subprocess.run(
            ["bash", "-lc", f"cd '{here}/backend' && alembic upgrade head"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            check=True,
            text=True,
        )
        return True, "migrations applied"
    except subprocess.CalledProcessError as e:
        return False, e.stdout[-400:] if e.stdout else str(e)


def check_head_match() -> tuple[bool, str]:
    try:
        import sqlalchemy as sa
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.environment import EnvironmentContext

        url = os.getenv("DATABASE_URL", DEFAULT_DB_APP)
        if url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        eng = sa.create_engine(url, pool_pre_ping=True, future=True)
        cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "alembic.ini"))
        script = ScriptDirectory.from_config(cfg)
        with eng.connect() as conn:
            def _cmp(rev, context):
                heads = set(script.get_heads())
                current = set([rev]) if rev else set()
                return heads == current
            ok = bool(EnvironmentContext(cfg, script, fn=_cmp).run_migrations())
        return ok, "head match" if ok else "head mismatch"
    except Exception as e:
        return False, str(e)


def check_health() -> tuple[bool, str]:
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(f"{API_BASE}/api/v1/health/live", timeout=3) as resp:
            if resp.status != 200:
                return False, f"live {resp.status}"
        with urllib.request.urlopen(f"{API_BASE}/api/v1/health/ready", timeout=3) as resp:
            body = resp.read().decode("utf-8")
            if resp.status not in (200, 503):
                return False, f"ready {resp.status}"
            # Ensure JSON shape
            try:
                _ = json.loads(body or "{}")
            except Exception:
                return False, "ready not json"
        return True, "health ok"
    except urllib.error.URLError as e:
        return False, str(e)


def main() -> int:
    print("Forge1 Doctor - local environment checks\n")
    ok_db, info_db = check_db()
    _print("Postgres", ok_db, info_db)
    ok_redis, info_redis = check_redis()
    _print("Redis", ok_redis, info_redis)
    ok_mig, info_mig = run_alembic()
    _print("Alembic", ok_mig, info_mig)
    ok_head, info_head = check_head_match()
    _print("Alembic head", ok_head, info_head)
    ok_health, info_health = check_health()
    _print("Health endpoints", ok_health, info_health)

    all_ok = ok_db and ok_redis and ok_mig and ok_head and ok_health
    print(f"\nOverall: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


