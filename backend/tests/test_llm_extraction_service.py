"""Unit tests for LLMExtractionService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic

from app.services.llm_extraction_service import LLMExtractionService
from app.services.exceptions import LLMInvalidResponseError, LLMUnavailableError


@pytest.fixture
def mock_client():
    """Create a mock AsyncAnthropic client."""
    return AsyncMock(spec=anthropic.AsyncAnthropic)


@pytest.fixture
def service(mock_client):
    """Create an LLMExtractionService with a mocked client."""
    return LLMExtractionService(client=mock_client)


def _make_message_response(text: str):
    """Helper to create a mock Claude message response."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    message = MagicMock()
    message.content = [text_block]
    return message


def _make_empty_message_response():
    """Helper to create a mock Claude response with empty content."""
    message = MagicMock()
    message.content = []
    return message


class TestLLMExtractionServiceExtract:
    """Tests for the extract() method."""

    @pytest.mark.asyncio
    async def test_extract_returns_raw_text_response(self, service, mock_client):
        """Test that extract() returns the raw text from Claude's response."""
        raw_json = '{"Nombre": "Juan Pérez", "Edad": "35"}'
        mock_client.messages.create = AsyncMock(
            return_value=_make_message_response(raw_json)
        )

        result = await service.extract("Extract fields from: mi nombre es Juan Pérez")

        assert result == raw_json
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_sends_prompt_to_claude(self, service, mock_client):
        """Test that extract() sends the given prompt to Claude API."""
        prompt = "Extract the following fields from the transcribed text..."
        mock_client.messages.create = AsyncMock(
            return_value=_make_message_response('{"field": "value"}')
        )

        await service.extract(prompt)

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["messages"] == [{"role": "user", "content": prompt}]
        assert call_args.kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_args.kwargs["max_tokens"] == 1024

    @pytest.mark.asyncio
    async def test_extract_raises_invalid_response_on_empty_content(
        self, service, mock_client
    ):
        """Test that LLMInvalidResponseError is raised when response has no content."""
        mock_client.messages.create = AsyncMock(
            return_value=_make_empty_message_response()
        )

        with pytest.raises(LLMInvalidResponseError) as exc_info:
            await service.extract("some prompt")

        assert exc_info.value.error_code == "LLM_INVALID_RESPONSE"

    @pytest.mark.asyncio
    async def test_extract_raises_invalid_response_on_whitespace_only_text(
        self, service, mock_client
    ):
        """Test that LLMInvalidResponseError is raised for whitespace-only responses."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "   \n  \t  "
        message = MagicMock()
        message.content = [text_block]

        mock_client.messages.create = AsyncMock(return_value=message)

        with pytest.raises(LLMInvalidResponseError) as exc_info:
            await service.extract("some prompt")

        assert exc_info.value.error_code == "LLM_INVALID_RESPONSE"

    @pytest.mark.asyncio
    async def test_extract_retries_on_connection_error_and_raises_unavailable(
        self, service, mock_client
    ):
        """Test that LLMUnavailableError is raised on connection errors after retries."""
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIConnectionError(request=MagicMock())
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMUnavailableError) as exc_info:
                await service.extract("some prompt")

        assert exc_info.value.error_code == "LLM_UNAVAILABLE"
        # Should have been called 3 times (1 initial + 2 retries)
        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_retries_on_timeout_error(self, service, mock_client):
        """Test that LLMUnavailableError is raised on timeout errors after retries."""
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APITimeoutError(request=MagicMock())
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMUnavailableError) as exc_info:
                await service.extract("some prompt")

        assert exc_info.value.error_code == "LLM_UNAVAILABLE"
        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_retries_on_5xx_server_error(self, service, mock_client):
        """Test that transient 5xx errors trigger retries."""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.json.return_value = {"error": {"message": "Internal Server Error"}}

        server_error = anthropic.InternalServerError(
            message="Internal Server Error",
            response=error_response,
            body={"error": {"message": "Internal Server Error"}},
        )

        mock_client.messages.create = AsyncMock(side_effect=server_error)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMUnavailableError):
                await service.extract("some prompt")

        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_succeeds_after_transient_failure(self, service, mock_client):
        """Test that extract succeeds if a retry attempt succeeds."""
        raw_json = '{"Nombre": "Ana"}'

        mock_client.messages.create = AsyncMock(
            side_effect=[
                anthropic.APIConnectionError(request=MagicMock()),
                _make_message_response(raw_json),
            ]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.extract("some prompt")

        assert result == raw_json
        assert mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_uses_exponential_backoff_delays(self, service, mock_client):
        """Test that retry delays follow exponential backoff (1s, 3s)."""
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIConnectionError(request=MagicMock())
        )

        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(LLMUnavailableError):
                await service.extract("some prompt")

        assert sleep_calls == [1, 3]

    @pytest.mark.asyncio
    async def test_extract_does_not_retry_on_auth_error(self, service, mock_client):
        """Test that 4xx errors (like auth) are not retried."""
        error_response = MagicMock()
        error_response.status_code = 401
        error_response.json.return_value = {"error": {"message": "Unauthorized"}}

        auth_error = anthropic.AuthenticationError(
            message="Unauthorized",
            response=error_response,
            body={"error": {"message": "Unauthorized"}},
        )

        mock_client.messages.create = AsyncMock(side_effect=auth_error)

        with pytest.raises(LLMUnavailableError):
            await service.extract("some prompt")

        # Should NOT retry - only 1 call
        assert mock_client.messages.create.call_count == 1


class TestLLMExtractionServiceTransientErrors:
    """Tests for transient error detection."""

    def test_connection_error_is_transient(self, service):
        """APIConnectionError should be considered transient."""
        error = anthropic.APIConnectionError(request=MagicMock())
        assert service._is_transient_error(error) is True

    def test_timeout_error_is_transient(self, service):
        """APITimeoutError should be considered transient."""
        error = anthropic.APITimeoutError(request=MagicMock())
        assert service._is_transient_error(error) is True

    def test_5xx_error_is_transient(self, service):
        """5xx status errors should be considered transient."""
        response = MagicMock()
        response.status_code = 503
        response.json.return_value = {"error": {"message": "Service Unavailable"}}

        error = anthropic.APIStatusError(
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

        error = anthropic.APIStatusError(
            message="Bad Request",
            response=response,
            body={"error": {"message": "Bad Request"}},
        )
        assert service._is_transient_error(error) is False

    def test_generic_exception_is_not_transient(self, service):
        """Generic exceptions should NOT be considered transient."""
        error = ValueError("some error")
        assert service._is_transient_error(error) is False
