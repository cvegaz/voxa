"""Unit tests for POST /api/extraction/process endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ExtractionResult, RecordValue
from app.services.exceptions import LLMInvalidResponseError, LLMUnavailableError


def _session_data(session_id: str, status: str = "confirmed") -> dict:
    """Create a mock session dict as returned by get_session_with_context."""
    return {
        "id": session_id,
        "schema_json": {
            "columns": [
                {"index": 1, "name": "Nombre", "data_type": "texto", "example_value": "Juan"},
                {"index": 2, "name": "Edad", "data_type": "número entero", "example_value": "30"},
            ]
        },
        "enriched_context": "Contexto enriquecido para extracción.",
        "file_path": "/tmp/test.xlsx",
        "dataframe_json": '[{"Nombre": "Juan", "Edad": "30"}]',
        "status": status,
    }


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    return MagicMock()


@pytest.fixture
def client(mock_pool):
    """Create a test client with mocked database pool."""
    app.state.pool = mock_pool
    return TestClient(app, raise_server_exceptions=False)


class TestExtractionProcessSuccess:
    """Tests for successful extraction processing."""

    @patch("app.routes.extraction_routes.ExtractionOrchestrator")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_valid_request_returns_200(self, MockRepo, MockOrch, client):
        """Valid extraction request returns 200 with ExtractionResult."""
        session_id = str(uuid4())
        extraction_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id)
        )

        mock_orch = MockOrch.return_value
        mock_orch.process = AsyncMock(
            return_value=ExtractionResult(
                extraction_id=extraction_id,
                record=[
                    RecordValue(column_name="Nombre", value="Carlos"),
                    RecordValue(column_name="Edad", value="25"),
                ],
                row_number=5,
            )
        )

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "El paciente se llama Carlos y tiene 25 años.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["extraction_id"] == extraction_id
        assert data["row_number"] == 5
        assert len(data["record"]) == 2
        assert data["record"][0]["column_name"] == "Nombre"
        assert data["record"][0]["value"] == "Carlos"

    @patch("app.routes.extraction_routes.ExtractionOrchestrator")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_orchestrator_called_with_correct_args(self, MockRepo, MockOrch, client):
        """Orchestrator.process() is called with session_id and transcribed_text."""
        session_id = str(uuid4())
        extraction_id = str(uuid4())
        text = "El paciente Carlos tiene 25 años."

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id)
        )

        mock_orch = MockOrch.return_value
        mock_orch.process = AsyncMock(
            return_value=ExtractionResult(
                extraction_id=extraction_id,
                record=[RecordValue(column_name="Nombre", value="Carlos")],
                row_number=4,
            )
        )

        response = client.post(
            "/api/extraction/process",
            json={"session_id": session_id, "transcribed_text": text},
        )

        assert response.status_code == 200
        mock_orch.process.assert_called_once_with(
            session_id=session_id,
            transcribed_text=text,
        )


class TestExtractionProcessSessionValidation:
    """Tests for session validation errors."""

    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_session_not_found_returns_404(self, MockRepo, client):
        """Non-existent session returns 404 with SESSION_NOT_FOUND."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(return_value=None)

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "Texto de prueba para extracción.",
            },
        )

        assert response.status_code == 404
        data = response.json()["detail"]
        assert data["error_code"] == "SESSION_NOT_FOUND"

    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_session_not_confirmed_returns_422(self, MockRepo, client):
        """Session with status != 'confirmed' returns 422 with SESSION_NOT_CONFIRMED."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id, status="pending")
        )

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "Texto de prueba para extracción.",
            },
        )

        assert response.status_code == 422
        data = response.json()["detail"]
        assert data["error_code"] == "SESSION_NOT_CONFIRMED"

    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_replaced_session_returns_422(self, MockRepo, client):
        """Session with status 'replaced' returns 422 with SESSION_NOT_CONFIRMED."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id, status="replaced")
        )

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "Texto de prueba.",
            },
        )

        assert response.status_code == 422
        data = response.json()["detail"]
        assert data["error_code"] == "SESSION_NOT_CONFIRMED"


class TestExtractionProcessInputValidation:
    """Tests for input validation (Pydantic model)."""

    def test_empty_text_returns_422(self, client):
        """Empty transcribed_text is rejected by Pydantic (min_length=1)."""
        session_id = str(uuid4())

        response = client.post(
            "/api/extraction/process",
            json={"session_id": session_id, "transcribed_text": ""},
        )

        assert response.status_code == 422

    def test_missing_transcribed_text_returns_422(self, client):
        """Missing transcribed_text field returns 422."""
        session_id = str(uuid4())

        response = client.post(
            "/api/extraction/process",
            json={"session_id": session_id},
        )

        assert response.status_code == 422

    def test_missing_session_id_returns_422(self, client):
        """Missing session_id field returns 422."""
        response = client.post(
            "/api/extraction/process",
            json={"transcribed_text": "Texto de prueba."},
        )

        assert response.status_code == 422

    def test_invalid_session_id_format_returns_422(self, client):
        """Non-UUID session_id returns 422."""
        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": "not-a-uuid",
                "transcribed_text": "Texto de prueba.",
            },
        )

        assert response.status_code == 422


class TestExtractionProcessLLMErrors:
    """Tests for LLM service error handling."""

    @patch("app.routes.extraction_routes.ExtractionOrchestrator")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_llm_unavailable_returns_502(self, MockRepo, MockOrch, client):
        """LLM unavailable error returns 502 with LLM_UNAVAILABLE."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id)
        )

        mock_orch = MockOrch.return_value
        mock_orch.process = AsyncMock(
            side_effect=LLMUnavailableError("Service unavailable after retries")
        )

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "Texto de prueba.",
            },
        )

        assert response.status_code == 502
        data = response.json()["detail"]
        assert data["error_code"] == "LLM_UNAVAILABLE"

    @patch("app.routes.extraction_routes.ExtractionOrchestrator")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_llm_invalid_response_returns_502(self, MockRepo, MockOrch, client):
        """LLM invalid response error returns 502 with LLM_INVALID_RESPONSE."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id)
        )

        mock_orch = MockOrch.return_value
        mock_orch.process = AsyncMock(
            side_effect=LLMInvalidResponseError("Response is not valid JSON")
        )

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "Texto de prueba.",
            },
        )

        assert response.status_code == 502
        data = response.json()["detail"]
        assert data["error_code"] == "LLM_INVALID_RESPONSE"


class TestExtractionProcessFileErrors:
    """Tests for file-related error handling."""

    @patch("app.routes.extraction_routes.ExtractionOrchestrator")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_file_not_found_returns_500(self, MockRepo, MockOrch, client):
        """FileNotFoundError returns 500 with FILE_NOT_FOUND."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id)
        )

        mock_orch = MockOrch.return_value
        mock_orch.process = AsyncMock(
            side_effect=FileNotFoundError("El archivo Excel no fue encontrado: /tmp/test.xlsx")
        )

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "Texto de prueba.",
            },
        )

        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["error_code"] == "FILE_NOT_FOUND"

    @patch("app.routes.extraction_routes.ExtractionOrchestrator")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_file_write_error_returns_500(self, MockRepo, MockOrch, client):
        """OSError during file write returns 500 with FILE_WRITE_ERROR."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id)
        )

        mock_orch = MockOrch.return_value
        mock_orch.process = AsyncMock(
            side_effect=OSError("Permission denied")
        )

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "Texto de prueba.",
            },
        )

        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["error_code"] == "FILE_WRITE_ERROR"


class TestExtractionProcessDatabaseErrors:
    """Tests for database error handling."""

    @patch("app.routes.extraction_routes.ExtractionOrchestrator")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_database_error_returns_500(self, MockRepo, MockOrch, client):
        """Unexpected exception returns 500 with DATABASE_ERROR."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_session_with_context = AsyncMock(
            return_value=_session_data(session_id)
        )

        mock_orch = MockOrch.return_value
        mock_orch.process = AsyncMock(
            side_effect=RuntimeError("Connection pool exhausted")
        )

        response = client.post(
            "/api/extraction/process",
            json={
                "session_id": session_id,
                "transcribed_text": "Texto de prueba.",
            },
        )

        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["error_code"] == "DATABASE_ERROR"
