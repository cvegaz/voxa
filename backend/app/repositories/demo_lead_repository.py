"""Repository for demo lead capture (demo_leads table, ADR-0019 §5)."""

from typing import Optional
from uuid import UUID

import asyncpg


class DemoLeadRepository:
    """Persists emails volunteered from inside the demo."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_lead(
        self,
        email: str,
        capture_point: str,
        session_id: Optional[UUID] = None,
        source_lang: Optional[str] = None,
    ) -> UUID:
        """Insert a lead and return its generated ID.

        Duplicates are allowed on purpose: the same visitor leaving an address at
        the download and again at the wall is two data points about which moment
        converts, not a mistake to deduplicate away at write time.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO demo_leads (email, capture_point, session_id, source_lang)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                email,
                capture_point,
                session_id,
                source_lang,
            )
            return row["id"]
