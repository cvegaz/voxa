"""Unit tests for LLMEnrichmentService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic

from app.models import ColumnDef, ColumnSchema
from app.services.llm_enrichment_service import LLMEnrichmentService
from app.services.exceptions import LLMInvalidResponseError, LLMUnavailableError


@pytest.fixture
def sample_schema():
    """Create a sample column schema for testing."""
    return ColumnSchema(
        columns=[
            ColumnDef(index=1, name="Nombre", data_type="texto", example_value="Juan Pérez"),
            ColumnDef(index=2, name="Edad", data_type="número entero", example_value="35"),
            ColumnDef(
                index=3,
                name="Fecha",
                data_type="fecha DD/MM/YYYY",
                example_value="15/03/2024",
            ),
        ]
    )


@pytest.fixture
def sample_context():
    """Create a sample context string for testing."""
    return (
        "Este Excel contiene un registro de pacientes de una clínica dental. "
        "Los datos se capturan durante la consulta médica mediante narración de audio."
    )


@pytest.fixture
def mock_client():
    """Create a mock AsyncAnthropic client."""
    return AsyncMock(spec=anthropic.AsyncAnthropic)


@pytest.fixture
def service(mock_client):
    """Create an LLMEnrichmentService with a mocked client."""
    return LLMEnrichmentService(client=mock_client)


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


class TestLLMEnrichmentServiceEnrich:
    """Tests for the enrich() method."""

    @pytest.mark.asyncio
    async def test_enrich_returns_enriched_context(
        self, service, mock_client, sample_context, sample_schema
    ):
        """Test that enrich() returns the text from Claude's response."""
        enriched = "Contexto enriquecido: pacientes clínica dental, campos: nombre, edad, fecha."
        mock_client.messages.create = AsyncMock(
            return_value=_make_message_response(enriched)
        )

        result = await service.enrich(sample_context, sample_schema)

        assert result == enriched
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_builds_prompt_with_context_and_schema(
        self, service, mock_client, sample_context, sample_schema
    ):
        """Test that the prompt sent to Claude includes user context and schema info."""
        mock_client.messages.create = AsyncMock(
            return_value=_make_message_response("enriched")
        )

        await service.enrich(sample_context, sample_schema)

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        prompt_content = messages[0]["content"]

        # Verify context is in the prompt
        assert sample_context in prompt_content

        # Verify schema columns are in the prompt
        assert "Nombre" in prompt_content
        assert "texto" in prompt_content
        assert "Juan Pérez" in prompt_content
        assert "Edad" in prompt_content
        assert "número entero" in prompt_content
        assert "Fecha" in prompt_content
        assert "fecha DD/MM/YYYY" in prompt_content

    @pytest.mark.asyncio
    async def test_enrich_raises_invalid_response_on_empty_content(
        self, service, mock_client, sample_context, sample_schema
    ):
        """Test that LLMInvalidResponseError is raised when response has no content."""
        mock_client.messages.create = AsyncMock(
            return_value=_make_empty_message_response()
        )

        with pytest.raises(LLMInvalidResponseError) as exc_info:
            await service.enrich(sample_context, sample_schema)

        assert exc_info.value.error_code == "LLM_INVALID_RESPONSE"

    @pytest.mark.asyncio
    async def test_enrich_raises_invalid_response_on_whitespace_only_text(
        self, service, mock_client, sample_context, sample_schema
    ):
        """Test that LLMInvalidResponseError is raised for whitespace-only responses."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "   \n  \t  "
        message = MagicMock()
        message.content = [text_block]

        mock_client.messages.create = AsyncMock(return_value=message)

        with pytest.raises(LLMInvalidResponseError) as exc_info:
            await service.enrich(sample_context, sample_schema)

        assert exc_info.value.error_code == "LLM_INVALID_RESPONSE"

    @pytest.mark.asyncio
    async def test_enrich_raises_unavailable_on_connection_error(
        self, service, mock_client, sample_context, sample_schema
    ):
        """Test that LLMUnavailableError is raised on connection errors after retries."""
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIConnectionError(request=MagicMock())
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMUnavailableError) as exc_info:
                await service.enrich(sample_context, sample_schema)

        assert exc_info.value.error_code == "LLM_UNAVAILABLE"
        # Should have been called 3 times (1 initial + 2 retries)
        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_enrich_raises_unavailable_on_timeout_error(
        self, service, mock_client, sample_context, sample_schema
    ):
        """Test that LLMUnavailableError is raised on timeout errors after retries."""
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APITimeoutError(request=MagicMock())
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMUnavailableError) as exc_info:
                await service.enrich(sample_context, sample_schema)

        assert exc_info.value.error_code == "LLM_UNAVAILABLE"
        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_enrich_retries_on_5xx_server_error(
        self, service, mock_client, sample_context, sample_schema
    ):
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
                await service.enrich(sample_context, sample_schema)

        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_enrich_succeeds_after_transient_failure(
        self, service, mock_client, sample_context, sample_schema
    ):
        """Test that enrich succeeds if a retry attempt succeeds."""
        enriched = "Contexto enriquecido generado correctamente."

        mock_client.messages.create = AsyncMock(
            side_effect=[
                anthropic.APIConnectionError(request=MagicMock()),
                _make_message_response(enriched),
            ]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.enrich(sample_context, sample_schema)

        assert result == enriched
        assert mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_enrich_does_not_retry_on_auth_error(
        self, service, mock_client, sample_context, sample_schema
    ):
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
            await service.enrich(sample_context, sample_schema)

        # Should NOT retry - only 1 call
        assert mock_client.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_enrich_uses_exponential_backoff_delays(
        self, service, mock_client, sample_context, sample_schema
    ):
        """Test that retry delays follow exponential backoff (1s, 3s)."""
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIConnectionError(request=MagicMock())
        )

        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(LLMUnavailableError):
                await service.enrich(sample_context, sample_schema)

        assert sleep_calls == [1, 3]


class TestLLMEnrichmentServiceBuildPrompt:
    """Tests for the _build_prompt() method."""

    def test_build_prompt_includes_all_columns(self, service, sample_schema):
        """Test that the prompt includes all column information."""
        context = "Contexto de prueba para verificar el prompt generado por el servicio."
        prompt = service._build_prompt(context, sample_schema)

        for col in sample_schema.columns:
            assert col.name in prompt
            assert col.data_type in prompt
            assert col.example_value in prompt

    def test_build_prompt_includes_user_context(self, service, sample_schema):
        """Test that the prompt includes the user-provided context."""
        context = "Este es el contexto personalizado del usuario para la plantilla."
        prompt = service._build_prompt(context, sample_schema)

        assert context in prompt

    def test_build_prompt_includes_extraction_instructions(self, service, sample_schema):
        """Test that the prompt asks Claude to enrich for audio transcription extraction."""
        context = "Contexto de prueba mínimo que cumple con la longitud requerida."
        prompt = service._build_prompt(context, sample_schema)

        assert "transcripciones de audio" in prompt
        assert "extracción" in prompt.lower() or "extraer" in prompt.lower()


class TestLLMEnrichmentServiceTransientErrors:
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
