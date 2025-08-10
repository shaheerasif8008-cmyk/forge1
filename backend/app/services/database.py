from typing import Optional

from psycopg_pool import AsyncConnectionPool


_pool: Optional[AsyncConnectionPool] = None


async def create_db_pool(dsn: str) -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(conninfo=dsn, open=False)
        await _pool.open()
        async with _pool.connection() as aconn:
            await aconn.execute("SELECT 1;")
    return _pool


def get_db_pool() -> AsyncConnectionPool:
    assert _pool is not None, "Database pool has not been initialized"
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


