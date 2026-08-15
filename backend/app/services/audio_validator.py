"""Audio file validation service.

Validates uploaded audio before it reaches Whisper:

- file must not be empty (0 bytes)
- file must not exceed the byte ceiling
- MIME type must be one of the allowed audio formats
- duration must be within the configured range

**On the duration argument (ADR-0019).** ``validate`` does not care where the
duration came from — but the caller must. Until 2026-08-14 the endpoint passed the
value the *client* reported in a form field, which made the cap unenforceable: a
request could claim 5 s while carrying ten minutes of audio, and Whisper billed the
ten. The route now measures the file with ``AudioDurationProbe`` and passes the
**measured** value. If you are wiring a new caller, pass a measurement, never a
client-supplied number.

The two-step shape (``validate_upload`` then ``validate``) exists so a caller can
reject an oversized or wrong-typed file **before** paying to decode it — the probe
writes a temp file and spawns a process, which is not work you want to do for
something already known to be invalid.
"""

from fastapi import UploadFile

from app.constants import (
    MAX_AUDIO_BYTES,
    MAX_AUDIO_DURATION_SECONDS,
    MIN_AUDIO_DURATION_SECONDS,
)
from app.models import ValidationResult


class AudioValidator:
    """Validates uploaded audio files for format, size and duration constraints."""

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
        max_bytes: int = MAX_AUDIO_BYTES,
    ):
        """Create a validator with configurable bounds.

        The defaults are the public-demo limits (ADR-0019); the overrides keep a
        future paid tier a configuration concern rather than a code change.
        """
        self.MIN_DURATION_SECONDS = min_duration_seconds
        self.MAX_DURATION_SECONDS = max_duration_seconds
        self.MAX_BYTES = max_bytes

    def validate(self, file: UploadFile, duration: float) -> ValidationResult:
        """Validate the upload and its duration.

        Validation is fail-fast: rejects at the first error found.

        Args:
            file: The uploaded audio file from FastAPI.
            duration: Duration in seconds. **Must be a server-side measurement of
                the file** (see the module docstring), never a client-reported value.

        Returns:
            ValidationResult with is_valid=True on success, or is_valid=False with
            error_code and detail on failure.
        """
        upload_result = self.validate_upload(file)
        if not upload_result.is_valid:
            return upload_result

        return self._validate_duration(duration)

    def validate_upload(self, file: UploadFile) -> ValidationResult:
        """Run only the cheap checks that need no decoding: emptiness, size, type.

        Callers run this *before* measuring the duration, so an obviously invalid
        upload never reaches the probe.
        """
        empty_result = self._validate_not_empty(file)
        if not empty_result.is_valid:
            return empty_result

        size_result = self._validate_size(file)
        if not size_result.is_valid:
            return size_result

        return self._validate_mime_type(file.content_type)

    def _file_size(self, file: UploadFile) -> int:
        """Size in bytes, leaving the stream rewound for the next reader."""
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        return size

    def _validate_not_empty(self, file: UploadFile) -> ValidationResult:
        """Check that the file is not empty (0 bytes)."""
        if self._file_size(file) == 0:
            return ValidationResult(
                is_valid=False,
                error_code="EMPTY_AUDIO_FILE",
                detail="El archivo de audio está vacío.",
            )

        return ValidationResult(is_valid=True)

    def _validate_size(self, file: UploadFile) -> ValidationResult:
        """Check the byte ceiling.

        This bounds *bytes*, not seconds — a low-bitrate file can hide many minutes
        under any reasonable cap, which is why the duration probe exists. Its job is
        to keep an absurd upload from being buffered and decoded at all.
        """
        if self._file_size(file) > self.MAX_BYTES:
            megabytes = self.MAX_BYTES / (1024 * 1024)
            return ValidationResult(
                is_valid=False,
                error_code="AUDIO_TOO_LARGE",
                detail=f"El archivo de audio supera el tamaño máximo de {megabytes:.0f} MB.",
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
