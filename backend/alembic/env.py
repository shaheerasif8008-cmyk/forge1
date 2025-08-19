import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.db.models import Base

target_metadata = Base.metadata


def _resolve_url() -> str:
    """Resolve database URL from env, -x url/db_url, or alembic.ini.

    Priority:
    1) DATABASE_URL or SQLALCHEMY_DATABASE_URL env vars
    2) -x url=... or -x db_url=...
    3) sqlalchemy.url from alembic.ini
    """
    url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URL")
    if not url:
        x = context.get_x_argument(as_dictionary=True)
        url = x.get("url") or x.get("db_url")
    if not url:
        url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise Exception(
            "DATABASE_URL not provided. Set env DATABASE_URL or run: "
            "alembic upgrade head -x url=postgresql+psycopg://user:pass@host:5432/db"
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = _resolve_url()
    # Optional diagnostics to STDOUT for CI/local debugging
    if os.getenv("ALEMBIC_DEBUG"):
        print(f"[alembic] Using URL: {url}")
    connectable = engine_from_config({"url": url, "echo": os.getenv("ALEMBIC_ECHO") == "1"}, prefix="", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
