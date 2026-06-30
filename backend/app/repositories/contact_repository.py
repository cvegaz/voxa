"""Repository for landing-page contact messages in PostgreSQL."""

from typing import Optional
from uuid import UUID

import asyncpg


class ContactRepository:
    """Handles persistence of contact-form submissions (contact_messages table)."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_message(
        self,
        name: str,
        email: str,
        message: str,
        company: Optional[str] = None,
        source_lang: Optional[str] = None,
    ) -> UUID:
        """Insert a new contact message and return its generated ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO contact_messages (
                    name, email, company, message, source_lang
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                name,
                email,
                company,
                message,
                source_lang,
            )
            return row["id"]
