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
        language: str = "es",
    ) -> None:
        """Update a session with enriched context and set status to 'confirmed'.

        Args:
            session_id: The UUID of the session to confirm.
            enriched_context: The LLM-generated enriched context.
            user_context: Optional original user-provided context.
            language: The session language ("es"/"en"), fixed at confirm time.

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
                    language = $3,
                    confirmed_at = $4
                WHERE id = $5
                  AND status = 'pending'
                """,
                enriched_context,
                user_context,
                language,
                datetime.now(timezone.utc),
                UUID(session_id),
            )
            if result == "UPDATE 0":
                raise ValueError(
                    f"Session {session_id} not found or not in 'pending' status"
                )

    async def mark_client_info(
        self,
        session_id: str,
        browser: Optional[str],
        platform: Optional[str],
    ) -> None:
        """Record which browser/platform this session came from (ADR-0019 §7).

        Best-effort telemetry: never raises when the session is gone, because a
        failure to record a diagnostic must not fail the user's request.
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE template_sessions
                SET client_browser = $1, client_platform = $2
                WHERE id = $3
                """,
                browser,
                platform,
                UUID(session_id),
            )

    async def mark_first_narration(self, session_id: str) -> None:
        """Stamp the "aha" moment — the first narration that made it through.

        ``IS NULL`` in the WHERE clause makes this **idempotent at the database**:
        the second and every later narration match nothing and change nothing.
        Enforcing "exactly once" here rather than with a read-then-write in the
        route removes the race between two concurrent narrations entirely — the
        row can only be claimed once.
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE template_sessions
                SET first_narration_at = $1
                WHERE id = $2 AND first_narration_at IS NULL
                """,
                datetime.now(timezone.utc),
                UUID(session_id),
            )

    async def mark_downloaded(self, session_id: str) -> None:
        """Stamp the first download. Idempotent, same reasoning as above:
        re-downloading is normal and must not look like a second conversion."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE template_sessions
                SET downloaded_at = $1
                WHERE id = $2 AND downloaded_at IS NULL
                """,
                datetime.now(timezone.utc),
                UUID(session_id),
            )

    async def mark_wall_hit(self, session_id: str, wall_kind: str) -> None:
        """Stamp the first wall this session ran into.

        ``wall_kind`` is 'trial' or 'budget'. First one wins, because the first is
        the one that actually stopped the visitor; whatever they hit afterwards is
        a consequence, not a cause.
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE template_sessions
                SET wall_hit_at = $1, wall_kind = $2
                WHERE id = $3 AND wall_hit_at IS NULL
                """,
                datetime.now(timezone.utc),
                wall_kind,
                UUID(session_id),
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
                       enriched_context, file_name, column_count, language,
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
                       enriched_context, file_name, column_count, language,
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
            language=row["language"],
            created_at=row["created_at"],
            confirmed_at=row["confirmed_at"],
            replaced_at=row["replaced_at"],
        )
