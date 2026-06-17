"""Repository for template session persistence in PostgreSQL."""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import asyncpg

from ..models.template_models import ColumnSchema, TemplateSession


class TemplateRepository:
    """Handles persistence of template sessions in PostgreSQL.

    Implements CRUD operations for the template_sessions table,
    managing session lifecycle (pending → confirmed → replaced).
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_session(
        self,
        schema: ColumnSchema,
        dataframe_json: str,
        file_name: str,
    ) -> str:
        """Create a new template session with status 'pending'.

        Args:
            schema: The extracted column schema from the Excel file.
            dataframe_json: JSON string of the DataFrame contents.
            file_name: Original filename of the uploaded Excel file.

        Returns:
            The session_id (UUID) as a string.
        """
        schema_json = json.dumps(schema.model_dump())
        column_count = len(schema.columns)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO template_sessions (
                    status, schema_json, dataframe_json, file_name, column_count
                )
                VALUES ('pending', $1::jsonb, $2::jsonb, $3, $4)
                RETURNING id
                """,
                schema_json,
                dataframe_json,
                file_name,
                column_count,
            )
            return str(row["id"])

    async def confirm_session(
        self,
        session_id: str,
        enriched_context: str,
        user_context: Optional[str] = None,
    ) -> None:
        """Update a session with enriched context and set status to 'confirmed'.

        Args:
            session_id: The UUID of the session to confirm.
            enriched_context: The LLM-generated enriched context.
            user_context: Optional original user-provided context.

        Raises:
            ValueError: If the session is not found or not in 'pending' status.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE template_sessions
                SET status = 'confirmed',
                    enriched_context = $1,
                    user_context = $2,
                    confirmed_at = $3
                WHERE id = $4
                  AND status = 'pending'
                """,
                enriched_context,
                user_context,
                datetime.now(timezone.utc),
                UUID(session_id),
            )
            if result == "UPDATE 0":
                raise ValueError(
                    f"Session {session_id} not found or not in 'pending' status"
                )

    async def get_active_session(self) -> Optional[TemplateSession]:
        """Retrieve the most recent confirmed session.

        Returns:
            The active TemplateSession, or None if no confirmed session exists.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, status, schema_json, dataframe_json, user_context,
                       enriched_context, file_name, column_count,
                       created_at, confirmed_at, replaced_at
                FROM template_sessions
                WHERE status = 'confirmed'
                ORDER BY confirmed_at DESC
                LIMIT 1
                """
            )
            if row is None:
                return None

            return self._row_to_session(row)

    async def replace_previous_sessions(self) -> int:
        """Mark all pending and confirmed sessions as 'replaced'.

        This is called before creating a new session to ensure only
        one active session exists at a time.

        Returns:
            The number of sessions that were marked as replaced.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE template_sessions
                SET status = 'replaced',
                    replaced_at = $1
                WHERE status IN ('pending', 'confirmed')
                """,
                datetime.now(timezone.utc),
            )
            # result format: "UPDATE N"
            count = int(result.split(" ")[1])
            return count

    async def get_session_by_id(self, session_id: str) -> Optional[TemplateSession]:
        """Retrieve a session by its ID.

        Args:
            session_id: The UUID of the session.

        Returns:
            The TemplateSession, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, status, schema_json, dataframe_json, user_context,
                       enriched_context, file_name, column_count,
                       created_at, confirmed_at, replaced_at
                FROM template_sessions
                WHERE id = $1
                """,
                UUID(session_id),
            )
            if row is None:
                return None

            return self._row_to_session(row)

    async def mark_session_replaced(self, session_id: str) -> bool:
        """Mark a specific session as replaced.

        Args:
            session_id: The UUID of the session to mark as replaced.

        Returns:
            True if the session was found and updated, False otherwise.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE template_sessions
                SET status = 'replaced',
                    replaced_at = $1
                WHERE id = $2
                  AND status IN ('pending', 'confirmed')
                """,
                datetime.now(timezone.utc),
                UUID(session_id),
            )
            return result != "UPDATE 0"

    def _row_to_session(self, row: asyncpg.Record) -> TemplateSession:
        """Convert a database row to a TemplateSession model."""
        schema_data = row["schema_json"]
        # asyncpg returns JSONB as a dict/list directly
        if isinstance(schema_data, str):
            schema_data = json.loads(schema_data)

        dataframe_json = row["dataframe_json"]
        if isinstance(dataframe_json, (dict, list)):
            dataframe_json = json.dumps(dataframe_json)

        return TemplateSession(
            id=row["id"],
            status=row["status"],
            column_schema=ColumnSchema(**schema_data),
            dataframe_json=dataframe_json,
            user_context=row["user_context"],
            enriched_context=row["enriched_context"],
            file_name=row["file_name"],
            column_count=row["column_count"],
            created_at=row["created_at"],
            confirmed_at=row["confirmed_at"],
            replaced_at=row["replaced_at"],
        )
