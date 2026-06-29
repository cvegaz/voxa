"""Audio file validation service.

Validates uploaded audio files before sending to Whisper API:
- MIME type must be one of the allowed audio formats
- Duration must be within the configured range (default 1.0s–20.0s)
- File must not be empty (0 bytes)
"""

from fastapi import UploadFile

from app.constants import MAX_AUDIO_DURATION_SECONDS, MIN_AUDIO_DURATION_SECONDS
from app.models import ValidationResult


class AudioValidator:
    """Validates uploaded audio files for format and duration constraints."""

    ALLOWED_MIME_TYPES = {
        "audio/webm",
        "audio/ogg",
        "audio/mp4",
        "audio/mpeg",
        "audio/wav",
    }

    def __init__(
        self,
        min_duration_seconds: float = MIN_AUDIO_DURATION_SECONDS,
        max_duration_seconds: float = MAX_AUDIO_DURATION_SECONDS,
    ):
        """Create a validator with configurable duration bounds.

        The defaults are the free-tier limits; a future paid tier can construct
        the validator with a larger ``max_duration_seconds``.
        """
        self.MIN_DURATION_SECONDS = min_duration_seconds
        self.MAX_DURATION_SECONDS = max_duration_seconds

    def validate(self, file: UploadFile, duration: float) -> ValidationResult:
        """Validate MIME type and duration of the uploaded audio file.

        Validation is fail-fast: rejects at the first error found.

        Args:
            file: The uploaded audio file from FastAPI.
            duration: Duration of the audio in seconds.

        Returns:
            ValidationResult with is_valid=True on success, or
            is_valid=False with error_code and detail on failure.
        """
        # 1. Validate file is not empty
        empty_result = self._validate_not_empty(file)
        if not empty_result.is_valid:
            return empty_result

        # 2. Validate MIME type
        mime_result = self._validate_mime_type(file.content_type)
        if not mime_result.is_valid:
            return mime_result

        # 3. Validate duration
        duration_result = self._validate_duration(duration)
        if not duration_result.is_valid:
            return duration_result

        return ValidationResult(is_valid=True)

    def _validate_not_empty(self, file: UploadFile) -> ValidationResult:
        """Check that the file is not empty (0 bytes)."""
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if size == 0:
            return ValidationResult(
                is_valid=False,
                error_code="EMPTY_AUDIO_FILE",
                detail="El archivo de audio está vacío.",
            )

        return ValidationResult(is_valid=True)

    def _validate_mime_type(self, content_type: str | None) -> ValidationResult:
        """Check that the MIME type is in the allowed set.

        Browsers append codec parameters to the MIME type (e.g.
        "audio/webm;codecs=opus"), so we compare only the base type that
        precedes any ";" parameter.
        """
        base_type = (
            content_type.split(";")[0].strip().lower() if content_type else None
        )
        if base_type is None or base_type not in self.ALLOWED_MIME_TYPES:
            allowed = ", ".join(sorted(self.ALLOWED_MIME_TYPES))
            return ValidationResult(
                is_valid=False,
                error_code="UNSUPPORTED_AUDIO_FORMAT",
                detail=f"El formato '{content_type}' no es compatible. Formatos permitidos: {allowed}.",
            )

        return ValidationResult(is_valid=True)

    def _validate_duration(self, duration: float) -> ValidationResult:
        """Check that the duration is within the allowed range."""
        if duration < self.MIN_DURATION_SECONDS:
            return ValidationResult(
                is_valid=False,
                error_code="AUDIO_TOO_SHORT",
                detail=f"El audio tiene una duración de {duration:.1f}s. La duración mínima es {self.MIN_DURATION_SECONDS}s.",
            )

        if duration > self.MAX_DURATION_SECONDS:
            return ValidationResult(
                is_valid=False,
                error_code="AUDIO_TOO_LONG",
                detail=f"El audio tiene una duración de {duration:.1f}s. La duración máxima es {self.MAX_DURATION_SECONDS}s.",
            )

        return ValidationResult(is_valid=True)
