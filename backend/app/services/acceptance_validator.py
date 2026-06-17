"""Acceptance validation service.

Validates preconditions for accepting a transcribed text:
- Transcription session exists and is in 'pending' status
- Text is non-empty and not whitespace-only
- A confirmed Esquema_Columnas (template session) exists
"""

from uuid import UUID

from app.models import ValidationResult
from app.repositories.template_repository import TemplateRepository
from app.repositories.transcription_repository import TranscriptionRepository


class AcceptanceValidator:
    """Validates preconditions before accepting a transcription."""

    def __init__(
        self,
        transcription_repository: TranscriptionRepository,
        template_repository: TemplateRepository,
    ) -> None:
        self._transcription_repo = transcription_repository
        self._template_repo = template_repository

    async def validate(self, transcription_id: UUID, text: str) -> ValidationResult:
        """Validate that a transcription can be accepted.

        Checks:
        1. Session exists and is in 'pending' status
        2. Text is non-empty and not whitespace-only
        3. A confirmed Esquema_Columnas exists

        Args:
            transcription_id: The UUID of the transcription session to accept.
            text: The final text to accept (possibly edited by the user).

        Returns:
            ValidationResult with is_valid=True on success, or
            is_valid=False with error_code and detail on failure.
        """
        # 1. Verify session exists and is in pending status
        session = await self._transcription_repo.get_session(transcription_id)
        if session is None or session.status != "pending":
            return ValidationResult(
                is_valid=False,
                error_code="SESSION_NOT_FOUND",
                detail=(
                    f"La sesión de transcripción {transcription_id} no fue encontrada "
                    "o no está en estado pendiente."
                ),
            )

        # 2. Verify text is non-empty and not whitespace-only
        if not text or not text.strip():
            return ValidationResult(
                is_valid=False,
                error_code="EMPTY_TRANSCRIPTION",
                detail="El texto de transcripción no puede estar vacío.",
            )

        # 3. Verify a confirmed schema exists
        active_session = await self._template_repo.get_active_session()
        if active_session is None:
            return ValidationResult(
                is_valid=False,
                error_code="NO_CONFIRMED_SCHEMA",
                detail=(
                    "No existe un Esquema_Columnas confirmado. "
                    "Primero debe cargar y confirmar un archivo Excel."
                ),
            )

        return ValidationResult(is_valid=True)
