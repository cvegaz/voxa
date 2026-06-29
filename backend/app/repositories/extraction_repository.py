"""Repository for extraction record persistence in PostgreSQL."""

import json
from typing import Optional
from uuid import UUID

import asyncpg

from ..database import get_pool


class ExtractionRepository:
    """Handles persistence of extraction records in PostgreSQL.

    Implements operations for saving extraction results, retrieving records,
    updating DataFrames, and fetching session context for the extraction flow.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save_extraction(
        self,
        session_id: str,
        record: dict,
        row_number: int,
        transcribed_text: str,
    ) -> str:
        """Save an extraction record and return the extraction_id.

        Args:
            session_id: The UUID of the template session.
            record: Dict mapping column names to extracted values.
            row_number: The row number in the Excel file (>= 4).
            transcribed_text: The original transcribed text used for extraction.

        Returns:
            The extraction_id (UUID) as a string.
        """
        record_json = json.dumps(record)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO extraction_records (
                    session_id, row_number, record_json, transcribed_text, status
                )
                VALUES ($1, $2, $3::jsonb, $4, 'completed')
                RETURNING id
                """,
                UUID(session_id),
                row_number,
                record_json,
                transcribed_text,
            )
            return str(row["id"])

    async def get_export_context(self, session_id: str) -> Optional[dict]:
        """Fetch what the export needs: the column schema and the file name.

        Used by the on-demand Excel export (ADR-0013), which rebuilds the .xlsx
        from the schema. Returns None if the session does not exist.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT schema_json, file_name FROM template_sessions WHERE id = $1",
                UUID(session_id),
            )
            if row is None:
                return None

            schema_json = row["schema_json"]
            if isinstance(schema_json, str):
                schema_json = json.loads(schema_json)

            return {"schema_json": schema_json, "file_name": row["file_name"]}

    async def get_status(self, session_id: str) -> Optional[str]:
        """Return the session status, or None if the session does not exist."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM template_sessions WHERE id = $1",
                UUID(session_id),
            )
            return row["status"] if row else None

    async def mark_finalized(self, session_id: str) -> None:
        """Mark a session as finalized (idempotent at the call site).

        A finalized session accepts no further extractions (ADR-0013).

        Raises:
            ValueError: If the session is not found.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE template_sessions SET status = 'finalized' WHERE id = $1",
                UUID(session_id),
            )
            if result == "UPDATE 0":
                raise ValueError(f"Session {session_id} not found")

    async def count_records(self, session_id: str) -> int:
        """Count the extraction records already saved for a session.

        This is the authoritative count used to derive the next ``row_number``
        (see ADR-0013): ``extraction_records`` is the single source of truth, so
        the row number is consistent with what the UI shows and can never drift
        from a parallel counter.

        Args:
            session_id: The UUID of the template session.

        Returns:
            The number of extraction records for the session.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS n FROM extraction_records WHERE session_id = $1",
                UUID(session_id),
            )
            return row["n"]

    async def get_records(self, session_id: str) -> list[dict]:
        """Retrieve all extraction records for a session, ordered by row_number ASC.

        Args:
            session_id: The UUID of the template session.

        Returns:
            List of dicts with extraction record data.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, session_id, row_number, record_json,
                       transcribed_text, status, error_message, created_at
                FROM extraction_records
                WHERE session_id = $1
                ORDER BY row_number ASC
                """,
                UUID(session_id),
            )

            records = []
            for row in rows:
                record_json = row["record_json"]
                if isinstance(record_json, str):
                    record_json = json.loads(record_json)

                records.append(
                    {
                        "id": str(row["id"]),
                        "session_id": str(row["session_id"]),
                        "row_number": row["row_number"],
                        "record_json": record_json,
                        "transcribed_text": row["transcribed_text"],
                        "status": row["status"],
                        "error_message": row["error_message"],
                        "created_at": row["created_at"],
                    }
                )

            return records

    async def get_session_with_context(self, session_id: str) -> Optional[dict]:
        """Fetch a session with schema, enriched_context, and file_path.

        Args:
            session_id: The UUID of the template session.

        Returns:
            Dict with session data (id, schema_json, enriched_context,
            file_path, dataframe_json, status), or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, schema_json, enriched_context, file_path,
                       dataframe_json, status
                FROM template_sessions
                WHERE id = $1
                """,
                UUID(session_id),
            )

            if row is None:
                return None

            schema_json = row["schema_json"]
            if isinstance(schema_json, str):
                schema_json = json.loads(schema_json)

            dataframe_json = row["dataframe_json"]
            if isinstance(dataframe_json, (dict, list)):
                dataframe_json = json.dumps(dataframe_json)

            return {
                "id": str(row["id"]),
                "schema_json": schema_json,
                "enriched_context": row["enriched_context"],
                "file_path": row["file_path"],
                "dataframe_json": dataframe_json,
                "status": row["status"],
            }
