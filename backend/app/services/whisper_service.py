"""Whisper Transcription Service.

Sends audio files to the OpenAI Whisper API for speech-to-text transcription.
Implements retry logic with exponential backoff for transient errors.
"""

import asyncio
import io
import os

import openai

from app.services.exceptions import (
    WhisperEmptyResponseError,
    WhisperNoSpeechError,
    WhisperUnavailableError,
)

# Map MIME types to file extensions expected by the OpenAI API
_MIME_TO_EXTENSION: dict[str, str] = {
    "audio/webm": "audio.webm",
    "audio/ogg": "audio.ogg",
    "audio/mp4": "audio.mp4",
    "audio/mpeg": "audio.mp3",
    "audio/wav": "audio.wav",
}


class WhisperTranscriptionService:
    """Transcribes audio using OpenAI Whisper API (whisper-1 model)."""

    MODEL = "whisper-1"
    # Default spoken language. We force a language (rather than let Whisper
    # auto-detect) so short clips don't waste tokens guessing — and sometimes
    # guessing wrong — which produced poor/partial transcriptions. The caller
    # passes the user's selected UI language (es/en) per request.
    DEFAULT_LANGUAGE = "es"
    MAX_RETRIES = 2
    BACKOFF_DELAYS = [1, 3]  # seconds for retry 1 and retry 2

    def __init__(self, client: openai.AsyncOpenAI | None = None):
        """Initialize with an optional pre-configured OpenAI async client.

        Args:
            client: An AsyncOpenAI client instance. If None, one is created
                    **lazily** on first use from the OPENAI_API_KEY env variable.
                    See ``LLMExtractionService.__init__`` for why the laziness is
                    load-bearing rather than a micro-optimisation.
        """
        self._explicit_client = client
        self._lazy_client: openai.AsyncOpenAI | None = None

    @property
    def _client(self) -> openai.AsyncOpenAI:
        """The injected client, or one built on first use."""
        if self._explicit_client is not None:
            return self._explicit_client
        if self._lazy_client is None:
            self._lazy_client = openai.AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY", ""),
            )
        return self._lazy_client

    def _get_filename(self, mime_type: str) -> str:
        """Get the appropriate filename with extension for the given MIME type.

        Args:
            mime_type: The MIME type of the audio file.

        Returns:
            A filename string with the correct extension.
        """
        return _MIME_TO_EXTENSION.get(mime_type, "audio.webm")

    def _is_transient_error(self, error: Exception) -> bool:
        """Determine if an error is transient and worth retrying.

        Transient errors include network issues, timeouts, and 5xx server errors.
        """
        if isinstance(error, (openai.APIConnectionError, openai.APITimeoutError)):
            return True
        if isinstance(error, openai.APIStatusError) and error.status_code >= 500:
            return True
        return False

    def _is_no_speech_error(self, error: Exception) -> bool:
        """Determine if the error indicates no speech was detected."""
        if isinstance(error, openai.APIStatusError):
            # OpenAI may return a 400 with a message about no speech
            error_message = str(error.message).lower() if hasattr(error, "message") else ""
            body_str = str(error.body).lower() if hasattr(error, "body") else ""
            return "no speech" in error_message or "no speech" in body_str
        return False

    async def transcribe(
        self, audio_file: bytes, mime_type: str, language: str | None = None
    ) -> str:
        """Send audio to Whisper API and return the transcribed text.

        Args:
            audio_file: The raw audio bytes.
            mime_type: The MIME type of the audio (e.g., "audio/webm").
            language: ISO-639-1 code of the expected spoken language (e.g. "es",
                "en"). Defaults to ``DEFAULT_LANGUAGE`` when not provided.

        Returns:
            The transcribed text string.

        Raises:
            WhisperUnavailableError: If the API is unreachable after retries.
            WhisperEmptyResponseError: If the API returns empty text.
            WhisperNoSpeechError: If no speech is detected in the audio.
        """
        filename = self._get_filename(mime_type)
        language = language or self.DEFAULT_LANGUAGE
        last_error: Exception | None = None

        for attempt in range(1 + self.MAX_RETRIES):
            try:
                file_obj = io.BytesIO(audio_file)
                file_obj.name = filename

                transcription = await self._client.audio.transcriptions.create(
                    model=self.MODEL,
                    file=(filename, file_obj, mime_type),
                    language=language,
                    temperature=0,
                )

                text = transcription.text.strip() if transcription.text else ""

                if not text:
                    raise WhisperEmptyResponseError()

                return text

            except (WhisperEmptyResponseError, WhisperNoSpeechError):
                # Don't retry our own custom errors
                raise

            except Exception as e:
                last_error = e

                # Check for no-speech error (not retryable)
                if self._is_no_speech_error(e):
                    raise WhisperNoSpeechError() from e

                if self._is_transient_error(e) and attempt < self.MAX_RETRIES:
                    delay = self.BACKOFF_DELAYS[attempt]
                    await asyncio.sleep(delay)
                    continue

                # Non-transient error or exhausted retries
                if self._is_transient_error(e):
                    raise WhisperUnavailableError(
                        f"El servicio Whisper no está disponible tras "
                        f"{self.MAX_RETRIES} reintentos. Error: {str(e)}"
                    ) from e

                # Non-transient API errors (e.g., 4xx auth errors)
                raise WhisperUnavailableError(
                    f"Error al comunicarse con el servicio Whisper: {str(e)}"
                ) from e

        # Safety net — should not reach here
        raise WhisperUnavailableError(
            f"El servicio Whisper no está disponible tras {self.MAX_RETRIES} reintentos."
        ) from last_error
