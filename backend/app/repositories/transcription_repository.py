"""Repository for transcription session persistence in PostgreSQL."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import asyncpg

from ..models.transcription_models import TranscriptionSession


class TranscriptionRepository:
    """Handles persistence of transcription sessions in PostgreSQL.

    Implements CRUD operations for the transcription_sessions table,
    managing session lifecycle (pending → accepted / discarded).
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_session(
        self,
        template_session_id: UUID,
        text: str,
        duration_seconds: float,
    ) -> UUID:
        """Create a new transcription session with status 'pending'.

        Args:
            template_session_id: The UUID of the associated template session.
            text: The original transcribed text from Whisper.
            duration_seconds: Duration of the audio recording in seconds.

        Returns:
            The transcription session ID as a UUID.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO transcription_sessions (
                    template_session_id, status, original_text, duration_seconds
                )
                VALUES ($1, 'pending', $2, $3)
                RETURNING id
                """,
                template_session_id,
                text,
                duration_seconds,
            )
            return row["id"]

    async def accept_session(
        self,
        transcription_id: UUID,
        final_text: str,
    ) -> None:
        """Mark a transcription session as accepted with the final text.

        Updates the session status to 'accepted', stores the final text
        (which may have been edited by the user), and sets the accepted_at
        timestamp.

        Args:
            transcription_id: The UUID of the transcription session.
            final_text: The final text to persist (possibly edited by the user).

        Raises:
            ValueError: If the session is not found or not in 'pending' status.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE transcription_sessions
                SET status = 'accepted',
                    final_text = $1,
                    accepted_at = $2
                WHERE id = $3
                  AND status = 'pending'
                """,
                final_text,
                datetime.now(timezone.utc),
                transcription_id,
            )
            if result == "UPDATE 0":
                raise ValueError(
                    f"Transcription session {transcription_id} not found or not in 'pending' status"
                )

    async def discard_session(self, transcription_id: UUID) -> None:
        """Mark a transcription session as discarded.

        Updates the session status to 'discarded' and sets the discarded_at
        timestamp. Used when the user presses "Agregar nuevo" to reset.

        Args:
            transcription_id: The UUID of the transcription session.

        Raises:
            ValueError: If the session is not found or not in 'pending' status.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE transcription_sessions
                SET status = 'discarded',
                    discarded_at = $1
                WHERE id = $2
                  AND status = 'pending'
                """,
                datetime.now(timezone.utc),
                transcription_id,
            )
            if result == "UPDATE 0":
                raise ValueError(
                    f"Transcription session {transcription_id} not found or not in 'pending' status"
                )

    async def get_session(
        self, transcription_id: UUID
    ) -> Optional[TranscriptionSession]:
        """Retrieve a transcription session by its ID.

        Args:
            transcription_id: The UUID of the transcription session.

        Returns:
            The TranscriptionSession, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, template_session_id, status, original_text,
                       final_text, duration_seconds, created_at,
                       accepted_at, discarded_at
                FROM transcription_sessions
                WHERE id = $1
                """,
                transcription_id,
            )
            if row is None:
                return None

            return TranscriptionSession(
                id=row["id"],
                template_session_id=row["template_session_id"],
                status=row["status"],
                original_text=row["original_text"],
                final_text=row["final_text"],
                duration_seconds=float(row["duration_seconds"]),
                created_at=row["created_at"],
                accepted_at=row["accepted_at"],
                discarded_at=row["discarded_at"],
            )
