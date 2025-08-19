import os
import sys

# Ensure project root is importable as `app`
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Force test database to local compose default unless explicitly provided
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local",
)
os.environ.setdefault(
    "SQLALCHEMY_DATABASE_URL",
    "postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local",
)
os.environ.setdefault("ENV", "dev")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6382/0")

# Apply Alembic migrations immediately on import so app modules see a ready DB
try:
    from alembic.config import Config
    from alembic import command
    cfg_path = os.path.join(ROOT, "alembic.ini")
    cfg = Config(cfg_path)
    cfg.set_main_option("script_location", os.path.join(ROOT, "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")
    # Import or reload the app after migrations so it sees the ready schema and env
    import importlib
    import app.main as app_main  # noqa: F401
    importlib.reload(app_main)
    # Diagnostics: ensure app engine points to same DB URL
    try:
        import app.db.session as app_session
        print(f"[tests] engine.url={app_session.engine.url}")
        # Safety net for dev/CI: ensure all tables exist after migration
        from app.db.models import Base
        Base.metadata.create_all(bind=app_session.engine)
        # Ensure common test tenants exist
        from sqlalchemy import text as _text
        with app_session.engine.begin() as conn:
            conn.execute(_text("INSERT INTO tenants (id, name, created_at) VALUES ('t-hook','Test Hook', NOW()) ON CONFLICT (id) DO NOTHING"))
            conn.execute(_text("INSERT INTO tenants (id, name, created_at) VALUES ('t-e2e','E2E', NOW()) ON CONFLICT (id) DO NOTHING"))
    except Exception as _e:  # pragma: no cover
        print(f"[tests] engine.url unavailable: {_e}")
except Exception as e:  # pragma: no cover - diagnostics in CI
    print(f"[tests] Alembic pre-upgrade skipped/failed: {e}")
# Apply Alembic migrations once per test session so runtime never does DDL
def pytest_sessionstart(session):  # type: ignore[no-redef]
    from alembic.config import Config
    from alembic import command
    from app.db.session import _make_engine_url
    import importlib
    import app.core.config as app_config
    import app.db.session as app_session
    cfg_path = os.path.join(ROOT, "alembic.ini")
    cfg = Config(cfg_path)
    cfg.set_main_option("script_location", os.path.join(ROOT, "alembic"))
    url = _make_engine_url()
    # Ensure env resolver uses the same URL
    os.environ["DATABASE_URL"] = url
    cfg.set_main_option("sqlalchemy.url", url)
    try:
        command.upgrade(cfg, "head")
    except Exception as e:
        print(f"[tests] Alembic upgrade skipped/failed: {e}")
    # Reload settings and session so app uses the same DATABASE_URL and a fresh engine
    importlib.reload(app_config)
    importlib.reload(app_session)
    # Seed tenants unconditionally
    try:
        from sqlalchemy import text as _text
        with app_session.engine.begin() as conn:
            conn.execute(_text("INSERT INTO tenants (id, name, beta, created_at) VALUES ('t-hook','Test Hook', false, CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING"))
            conn.execute(_text("INSERT INTO tenants (id, name, beta, created_at) VALUES ('t-e2e','E2E', false, CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING"))
    except Exception as e:
        print(f"[tests] tenant seed failed: {e}")
