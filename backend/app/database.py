"""Database connection management using asyncpg."""

import os
from typing import Optional

import asyncpg


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # Host port 5330 = voxa's reserved "+30 database" slot (~/Dev/PORTS.md).
    # 5432 (the old default) is a default-magnet port that belongs to whatever
    # Postgres the machine happens to run.
    "postgresql://postgres:postgres@localhost:5330/db_audio_excel",
)


_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
