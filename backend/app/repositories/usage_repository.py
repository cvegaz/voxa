"""Repository for the billable-operation ledger (usage_ledger table, ADR-0019 §3)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

import asyncpg


class UsageRepository:
    """Records billable operations and answers "how much have we spent since X?"."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record(
        self,
        operation: str,
        estimated_cost_usd: Decimal,
        session_id: Optional[UUID] = None,
    ) -> None:
        """Append one operation to the ledger."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO usage_ledger (operation, estimated_cost_usd, session_id)
                VALUES ($1, $2, $3)
                """,
                operation,
                estimated_cost_usd,
                session_id,
            )

    async def spent_since(self, instant: datetime) -> Decimal:
        """Total estimated spend recorded at or after ``instant``.

        COALESCE so an empty ledger answers 0 rather than NULL — the caller does
        arithmetic on this and a None would surface as a TypeError at the worst
        possible moment (the first request after a deploy).
        """
        async with self._pool.acquire() as conn:
            value = await conn.fetchval(
                """
                SELECT COALESCE(SUM(estimated_cost_usd), 0)
                FROM usage_ledger
                WHERE created_at >= $1
                """,
                instant,
            )
            return Decimal(value)
