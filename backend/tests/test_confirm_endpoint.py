"""Unit tests for POST /api/templates/confirm endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ColumnDef, ColumnSchema, TemplateSession


def _make_session(session_id: str, status: str = "pending") -> TemplateSession:
    """Create a mock TemplateSession for testing."""
    return TemplateSession(
        id=session_id,
        status=status,
        column_schema=ColumnSchema(
            columns=[
                ColumnDef(index=1, name="Nombre", data_type="texto", example_value="Juan"),
                ColumnDef(index=2, name="Edad", data_type="número entero", example_value="30"),
            ]
        ),
        dataframe_json='[{"Nombre": "Juan", "Edad": "30"}]',
        file_name="test.xlsx",
        column_count=2,
        created_at="2024-01-01T00:00:00+00:00",
    )


def _valid_context() -> str:
    """Return a valid context string (>= 50 chars)."""
    return (
        "Este archivo Excel contiene un registro de pacientes con sus datos personales "
        "y diagnósticos médicos capturados durante consultas presenciales."
    )


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    pool = MagicMock()
    return pool


@pytest.fixture
def client(mock_pool):
    """Create a test client with mocked database pool."""
    app.state.pool = mock_pool
    return TestClient(app, raise_server_exceptions=False)


class TestConfirmEndpointSuccess:
    """Tests for successful session confirmation."""

    @patch("app.routes.template_routes.LLMEnrichmentService")
    @patch("app.routes.template_routes.TemplateRepository")
    def test_valid_confirm_returns_200(self, MockRepo, MockLLM, client):
        """Valid confirm request returns 200 with enriched_context."""
        session_id = str(uuid4())
        session = _make_session(session_id)
        enriched = "Contexto enriquecido generado por el LLM con información detallada."

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)
        mock_repo.confirm_session = AsyncMock(return_value=None)

        mock_llm = MockLLM.return_value
        mock_llm.enrich = AsyncMock(return_value=enriched)

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": _valid_context()},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enrichedContext"] == enriched

    @patch("app.routes.template_routes.LLMEnrichmentService")
    @patch("app.routes.template_routes.TemplateRepository")
    def test_confirm_calls_llm_with_schema(self, MockRepo, MockLLM, client):
        """Confirm endpoint passes context and schema to LLM service."""
        session_id = str(uuid4())
        session = _make_session(session_id)
        context = _valid_context()
        enriched = "Enriched context text from Claude."

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)
        mock_repo.confirm_session = AsyncMock(return_value=None)

        mock_llm = MockLLM.return_value
        mock_llm.enrich = AsyncMock(return_value=enriched)

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": context},
        )

        assert response.status_code == 200
        mock_llm.enrich.assert_called_once_with(
            context=context,
            schema=session.column_schema,
        )

    @patch("app.routes.template_routes.LLMEnrichmentService")
    @patch("app.routes.template_routes.TemplateRepository")
    def test_confirm_persists_enriched_context(self, MockRepo, MockLLM, client):
        """Confirm endpoint persists the enriched context via repository."""
        session_id = str(uuid4())
        session = _make_session(session_id)
        context = _valid_context()
        enriched = "Enriched context persisted."

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)
        mock_repo.confirm_session = AsyncMock(return_value=None)

        mock_llm = MockLLM.return_value
        mock_llm.enrich = AsyncMock(return_value=enriched)

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": context},
        )

        assert response.status_code == 200
        mock_repo.confirm_session.assert_called_once_with(
            session_id=session_id,
            enriched_context=enriched,
            user_context=context,
        )


class TestConfirmEndpointSessionNotFound:
    """Tests for session not found or not pending."""

    @patch("app.routes.template_routes.TemplateRepository")
    def test_nonexistent_session_returns_404(self, MockRepo, client):
        """Non-existent session ID returns 404 with SESSION_NOT_FOUND."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=None)

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": _valid_context()},
        )

        assert response.status_code == 404
        assert response.json()["errorCode"] == "SESSION_NOT_FOUND"

    @patch("app.routes.template_routes.TemplateRepository")
    def test_confirmed_session_returns_404(self, MockRepo, client):
        """Session with status 'confirmed' returns 404."""
        session_id = str(uuid4())
        session = _make_session(session_id, status="confirmed")

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": _valid_context()},
        )

        assert response.status_code == 404
        assert response.json()["errorCode"] == "SESSION_NOT_FOUND"

    @patch("app.routes.template_routes.TemplateRepository")
    def test_replaced_session_returns_404(self, MockRepo, client):
        """Session with status 'replaced' returns 404."""
        session_id = str(uuid4())
        session = _make_session(session_id, status="replaced")

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": _valid_context()},
        )

        assert response.status_code == 404
        assert response.json()["errorCode"] == "SESSION_NOT_FOUND"


class TestConfirmEndpointContextValidation:
    """Tests for context validation errors."""

    @patch("app.routes.template_routes.TemplateRepository")
    def test_context_too_short_returns_422(self, MockRepo, client):
        """Context shorter than 50 characters returns 422 with CONTEXT_TOO_SHORT."""
        session_id = str(uuid4())
        session = _make_session(session_id)

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": "Texto corto insuficiente para el contexto."},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "CONTEXT_TOO_SHORT"

    @patch("app.routes.template_routes.TemplateRepository")
    def test_context_too_long_returns_422(self, MockRepo, client):
        """Context exceeding 3000 characters returns 422 with CONTEXT_TOO_LONG."""
        session_id = str(uuid4())
        session = _make_session(session_id)

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)

        long_context = "A" * 3001
        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": long_context},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "CONTEXT_TOO_LONG"


class TestConfirmEndpointLLMErrors:
    """Tests for LLM service error handling."""

    @patch("app.routes.template_routes.LLMEnrichmentService")
    @patch("app.routes.template_routes.TemplateRepository")
    def test_llm_unavailable_returns_502(self, MockRepo, MockLLM, client):
        """LLM unavailable error returns 502 with LLM_UNAVAILABLE."""
        from app.services.exceptions import LLMUnavailableError

        session_id = str(uuid4())
        session = _make_session(session_id)

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)

        mock_llm = MockLLM.return_value
        mock_llm.enrich = AsyncMock(
            side_effect=LLMUnavailableError("Service unavailable after retries")
        )

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": _valid_context()},
        )

        assert response.status_code == 502
        assert response.json()["errorCode"] == "LLM_UNAVAILABLE"

    @patch("app.routes.template_routes.LLMEnrichmentService")
    @patch("app.routes.template_routes.TemplateRepository")
    def test_llm_invalid_response_returns_502(self, MockRepo, MockLLM, client):
        """LLM invalid response error returns 502 with LLM_INVALID_RESPONSE."""
        from app.services.exceptions import LLMInvalidResponseError

        session_id = str(uuid4())
        session = _make_session(session_id)

        mock_repo = MockRepo.return_value
        mock_repo.get_session_by_id = AsyncMock(return_value=session)

        mock_llm = MockLLM.return_value
        mock_llm.enrich = AsyncMock(
            side_effect=LLMInvalidResponseError("Empty response from LLM")
        )

        response = client.post(
            "/api/templates/confirm",
            json={"session_id": session_id, "context": _valid_context()},
        )

        assert response.status_code == 502
        assert response.json()["errorCode"] == "LLM_INVALID_RESPONSE"


class TestConfirmEndpointRequestValidation:
    """Tests for request body validation (Pydantic)."""

    def test_missing_session_id_returns_422(self, client):
        """Missing session_id field returns 422."""
        response = client.post(
            "/api/templates/confirm",
            json={"context": _valid_context()},
        )
        assert response.status_code == 422

    def test_missing_context_returns_422(self, client):
        """Missing context field returns 422."""
        response = client.post(
            "/api/templates/confirm",
            json={"session_id": str(uuid4())},
        )
        assert response.status_code == 422

    def test_invalid_session_id_format_returns_422(self, client):
        """Non-UUID session_id returns 422."""
        response = client.post(
            "/api/templates/confirm",
            json={"session_id": "not-a-uuid", "context": _valid_context()},
        )
        assert response.status_code == 422
