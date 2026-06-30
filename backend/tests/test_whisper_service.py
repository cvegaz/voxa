"""Unit tests for WhisperTranscriptionService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import openai

from app.services.whisper_service import WhisperTranscriptionService
from app.services.exceptions import (
    WhisperEmptyResponseError,
    WhisperNoSpeechError,
    WhisperUnavailableError,
)


@pytest.fixture
def mock_client():
    """Create a mock AsyncOpenAI client."""
    client = AsyncMock(spec=openai.AsyncOpenAI)
    client.audio = MagicMock()
    client.audio.transcriptions = MagicMock()
    client.audio.transcriptions.create = AsyncMock()
    return client


@pytest.fixture
def service(mock_client):
    """Create a WhisperTranscriptionService with a mocked client."""
    return WhisperTranscriptionService(client=mock_client)


@pytest.fixture
def sample_audio():
    """Sample audio bytes for testing."""
    return b"\x00\x01\x02\x03" * 100


def _make_transcription_response(text: str):
    """Helper to create a mock Whisper transcription response."""
    response = MagicMock()
    response.text = text
    return response


class TestWhisperTranscriptionServiceTranscribe:
    """Tests for the transcribe() method."""

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self, service, mock_client, sample_audio):
        """Test that transcribe() returns the transcribed text."""
        expected_text = "Hola, este es un texto de prueba."
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response(expected_text)
        )

        result = await service.transcribe(sample_audio, "audio/webm")

        assert result == expected_text
        mock_client.audio.transcriptions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_sends_correct_model(self, service, mock_client, sample_audio):
        """Test that transcribe() sends the whisper-1 model."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("texto")
        )

        await service.transcribe(sample_audio, "audio/webm")

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["model"] == "whisper-1"

    @pytest.mark.asyncio
    async def test_transcribe_sends_spanish_language(self, service, mock_client, sample_audio):
        """Test that transcribe() pins the language to Spanish for accuracy."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("texto")
        )

        await service.transcribe(sample_audio, "audio/webm")

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["language"] == "es"

    @pytest.mark.asyncio
    async def test_transcribe_uses_provided_language(self, service, mock_client, sample_audio):
        """Test that transcribe() forwards the requested language to the API."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("text")
        )

        await service.transcribe(sample_audio, "audio/webm", "en")

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["language"] == "en"

    @pytest.mark.asyncio
    async def test_transcribe_sends_correct_mime_type(self, service, mock_client, sample_audio):
        """Test that transcribe() sends the file with correct MIME type."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("texto")
        )

        await service.transcribe(sample_audio, "audio/ogg")

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        # The file tuple should contain (filename, file_obj, mime_type)
        file_arg = call_kwargs["file"]
        assert file_arg[0] == "audio.ogg"
        assert file_arg[2] == "audio/ogg"

    @pytest.mark.asyncio
    async def test_transcribe_uses_webm_extension_for_webm_mime(
        self, service, mock_client, sample_audio
    ):
        """Test correct filename for audio/webm."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("texto")
        )

        await service.transcribe(sample_audio, "audio/webm")

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        file_arg = call_kwargs["file"]
        assert file_arg[0] == "audio.webm"

    @pytest.mark.asyncio
    async def test_transcribe_uses_mp3_extension_for_mpeg_mime(
        self, service, mock_client, sample_audio
    ):
        """Test correct filename for audio/mpeg."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("texto")
        )

        await service.transcribe(sample_audio, "audio/mpeg")

        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        file_arg = call_kwargs["file"]
        assert file_arg[0] == "audio.mp3"

    @pytest.mark.asyncio
    async def test_transcribe_raises_empty_response_on_empty_text(
        self, service, mock_client, sample_audio
    ):
        """Test WhisperEmptyResponseError when API returns empty text."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("")
        )

        with pytest.raises(WhisperEmptyResponseError) as exc_info:
            await service.transcribe(sample_audio, "audio/webm")

        assert exc_info.value.error_code == "WHISPER_EMPTY_RESPONSE"

    @pytest.mark.asyncio
    async def test_transcribe_raises_empty_response_on_whitespace_text(
        self, service, mock_client, sample_audio
    ):
        """Test WhisperEmptyResponseError when API returns whitespace-only text."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("   \n  \t  ")
        )

        with pytest.raises(WhisperEmptyResponseError) as exc_info:
            await service.transcribe(sample_audio, "audio/webm")

        assert exc_info.value.error_code == "WHISPER_EMPTY_RESPONSE"

    @pytest.mark.asyncio
    async def test_transcribe_raises_empty_response_on_none_text(
        self, service, mock_client, sample_audio
    ):
        """Test WhisperEmptyResponseError when API returns None text."""
        response = MagicMock()
        response.text = None
        mock_client.audio.transcriptions.create = AsyncMock(return_value=response)

        with pytest.raises(WhisperEmptyResponseError) as exc_info:
            await service.transcribe(sample_audio, "audio/webm")

        assert exc_info.value.error_code == "WHISPER_EMPTY_RESPONSE"

    @pytest.mark.asyncio
    async def test_transcribe_raises_no_speech_error(
        self, service, mock_client, sample_audio
    ):
        """Test WhisperNoSpeechError when API indicates no speech detected."""
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {"error": {"message": "No speech detected"}}

        no_speech_error = openai.BadRequestError(
            message="No speech detected in audio",
            response=error_response,
            body={"error": {"message": "No speech detected"}},
        )

        mock_client.audio.transcriptions.create = AsyncMock(side_effect=no_speech_error)

        with pytest.raises(WhisperNoSpeechError) as exc_info:
            await service.transcribe(sample_audio, "audio/webm")

        assert exc_info.value.error_code == "WHISPER_NO_SPEECH"

    @pytest.mark.asyncio
    async def test_transcribe_retries_on_connection_error(
        self, service, mock_client, sample_audio
    ):
        """Test that connection errors trigger retries."""
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=openai.APIConnectionError(request=MagicMock())
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(WhisperUnavailableError) as exc_info:
                await service.transcribe(sample_audio, "audio/webm")

        assert exc_info.value.error_code == "WHISPER_UNAVAILABLE"
        # 1 initial + 2 retries = 3 calls
        assert mock_client.audio.transcriptions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_transcribe_retries_on_timeout_error(
        self, service, mock_client, sample_audio
    ):
        """Test that timeout errors trigger retries."""
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=openai.APITimeoutError(request=MagicMock())
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(WhisperUnavailableError) as exc_info:
                await service.transcribe(sample_audio, "audio/webm")

        assert exc_info.value.error_code == "WHISPER_UNAVAILABLE"
        assert mock_client.audio.transcriptions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_transcribe_retries_on_5xx_error(
        self, service, mock_client, sample_audio
    ):
        """Test that 5xx server errors trigger retries."""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.json.return_value = {"error": {"message": "Internal Server Error"}}

        server_error = openai.InternalServerError(
            message="Internal Server Error",
            response=error_response,
            body={"error": {"message": "Internal Server Error"}},
        )

        mock_client.audio.transcriptions.create = AsyncMock(side_effect=server_error)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(WhisperUnavailableError):
                await service.transcribe(sample_audio, "audio/webm")

        assert mock_client.audio.transcriptions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_transcribe_succeeds_after_transient_failure(
        self, service, mock_client, sample_audio
    ):
        """Test that transcribe succeeds if a retry attempt succeeds."""
        expected_text = "Texto transcrito exitosamente."

        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=[
                openai.APIConnectionError(request=MagicMock()),
                _make_transcription_response(expected_text),
            ]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.transcribe(sample_audio, "audio/webm")

        assert result == expected_text
        assert mock_client.audio.transcriptions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_transcribe_does_not_retry_on_auth_error(
        self, service, mock_client, sample_audio
    ):
        """Test that 4xx errors (like auth) are not retried."""
        error_response = MagicMock()
        error_response.status_code = 401
        error_response.json.return_value = {"error": {"message": "Unauthorized"}}

        auth_error = openai.AuthenticationError(
            message="Unauthorized",
            response=error_response,
            body={"error": {"message": "Unauthorized"}},
        )

        mock_client.audio.transcriptions.create = AsyncMock(side_effect=auth_error)

        with pytest.raises(WhisperUnavailableError):
            await service.transcribe(sample_audio, "audio/webm")

        # Should NOT retry - only 1 call
        assert mock_client.audio.transcriptions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_transcribe_uses_exponential_backoff_delays(
        self, service, mock_client, sample_audio
    ):
        """Test that retry delays follow exponential backoff (1s, 3s)."""
        mock_client.audio.transcriptions.create = AsyncMock(
            side_effect=openai.APIConnectionError(request=MagicMock())
        )

        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(WhisperUnavailableError):
                await service.transcribe(sample_audio, "audio/webm")

        assert sleep_calls == [1, 3]

    @pytest.mark.asyncio
    async def test_transcribe_does_not_retry_empty_response(
        self, service, mock_client, sample_audio
    ):
        """Test that empty response errors are not retried."""
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value=_make_transcription_response("")
        )

        with pytest.raises(WhisperEmptyResponseError):
            await service.transcribe(sample_audio, "audio/webm")

        # Should only be called once - no retry
        assert mock_client.audio.transcriptions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_transcribe_does_not_retry_no_speech_error(
        self, service, mock_client, sample_audio
    ):
        """Test that no-speech errors are not retried."""
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {"error": {"message": "No speech detected"}}

        no_speech_error = openai.BadRequestError(
            message="No speech detected in audio",
            response=error_response,
            body={"error": {"message": "No speech detected"}},
        )

        mock_client.audio.transcriptions.create = AsyncMock(side_effect=no_speech_error)

        with pytest.raises(WhisperNoSpeechError):
            await service.transcribe(sample_audio, "audio/webm")

        # Should only be called once - no retry for validation errors
        assert mock_client.audio.transcriptions.create.call_count == 1


class TestWhisperTranscriptionServiceHelpers:
    """Tests for helper methods."""

    def test_get_filename_webm(self, service):
        """audio/webm maps to audio.webm."""
        assert service._get_filename("audio/webm") == "audio.webm"

    def test_get_filename_ogg(self, service):
        """audio/ogg maps to audio.ogg."""
        assert service._get_filename("audio/ogg") == "audio.ogg"

    def test_get_filename_mp4(self, service):
        """audio/mp4 maps to audio.mp4."""
        assert service._get_filename("audio/mp4") == "audio.mp4"

    def test_get_filename_mpeg(self, service):
        """audio/mpeg maps to audio.mp3."""
        assert service._get_filename("audio/mpeg") == "audio.mp3"

    def test_get_filename_wav(self, service):
        """audio/wav maps to audio.wav."""
        assert service._get_filename("audio/wav") == "audio.wav"

    def test_get_filename_unknown_defaults_to_webm(self, service):
        """Unknown MIME types default to audio.webm."""
        assert service._get_filename("audio/unknown") == "audio.webm"

    def test_connection_error_is_transient(self, service):
        """APIConnectionError should be considered transient."""
        error = openai.APIConnectionError(request=MagicMock())
        assert service._is_transient_error(error) is True

    def test_timeout_error_is_transient(self, service):
        """APITimeoutError should be considered transient."""
        error = openai.APITimeoutError(request=MagicMock())
        assert service._is_transient_error(error) is True

    def test_5xx_error_is_transient(self, service):
        """5xx status errors should be considered transient."""
        response = MagicMock()
        response.status_code = 503
        response.json.return_value = {"error": {"message": "Service Unavailable"}}

        error = openai.APIStatusError(
            message="Service Unavailable",
            response=response,
            body={"error": {"message": "Service Unavailable"}},
        )
        assert service._is_transient_error(error) is True

    def test_4xx_error_is_not_transient(self, service):
        """4xx status errors should NOT be considered transient."""
        response = MagicMock()
        response.status_code = 400
        response.json.return_value = {"error": {"message": "Bad Request"}}

        error = openai.APIStatusError(
            message="Bad Request",
            response=response,
            body={"error": {"message": "Bad Request"}},
        )
        assert service._is_transient_error(error) is False

    def test_generic_exception_is_not_transient(self, service):
        """Generic exceptions should NOT be considered transient."""
        error = ValueError("some error")
        assert service._is_transient_error(error) is False
