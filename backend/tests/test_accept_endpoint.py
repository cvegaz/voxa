"""Unit tests for POST /api/transcriptions/accept endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import TranscriptionSession, ValidationResult


def _make_transcription_session(
    transcription_id=None, status="pending"
) -> TranscriptionSession:
    """Create a mock TranscriptionSession for testing."""
    return TranscriptionSession(
        id=transcription_id or uuid4(),
        template_session_id=uuid4(),
        status=status,
        original_text="Texto original de prueba",
        final_text=None,
        duration_seconds=5.0,
        created_at="2024-01-01T00:00:00+00:00",
        accepted_at=None,
        discarded_at=None,
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


class TestAcceptEndpointSuccess:
    """Tests for successful acceptance flow."""

    @patch("app.routes.transcription_routes.AcceptanceValidator")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_valid_accept_returns_200(
        self, MockTranscriptionRepo, MockValidator, client
    ):
        """Valid accept request returns 200 with status 'accepted'."""
        transcription_id = str(uuid4())

        mock_validator = MockValidator.return_value
        mock_validator.validate = AsyncMock(
            return_value=ValidationResult(is_valid=True)
        )

        mock_transcription_repo = MockTranscriptionRepo.return_value
        mock_transcription_repo.accept_session = AsyncMock(return_value=None)

        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": transcription_id, "text": "Texto aceptado"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    @patch("app.routes.transcription_routes.AcceptanceValidator")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_accept_calls_repository(
        self, MockTranscriptionRepo, MockValidator, client
    ):
        """Accept endpoint calls accept_session on the repository with correct args."""
        transcription_id = str(uuid4())
        text = "Texto final editado por el usuario"

        mock_validator = MockValidator.return_value
        mock_validator.validate = AsyncMock(
            return_value=ValidationResult(is_valid=True)
        )

        mock_transcription_repo = MockTranscriptionRepo.return_value
        mock_transcription_repo.accept_session = AsyncMock(return_value=None)

        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": transcription_id, "text": text},
        )

        assert response.status_code == 200
        mock_transcription_repo.accept_session.assert_called_once_with(
            UUID(transcription_id), text
        )

    @patch("app.routes.transcription_routes.AcceptanceValidator")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_accept_calls_validator_with_correct_args(
        self, MockTranscriptionRepo, MockValidator, client
    ):
        """Accept endpoint passes transcription_id and text to the validator."""
        transcription_id = str(uuid4())
        text = "Texto para validar"

        mock_validator = MockValidator.return_value
        mock_validator.validate = AsyncMock(
            return_value=ValidationResult(is_valid=True)
        )

        mock_transcription_repo = MockTranscriptionRepo.return_value
        mock_transcription_repo.accept_session = AsyncMock(return_value=None)

        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": transcription_id, "text": text},
        )

        assert response.status_code == 200
        mock_validator.validate.assert_called_once_with(
            UUID(transcription_id), text
        )


class TestAcceptEndpointSessionNotFound:
    """Tests for session not found errors (404)."""

    @patch("app.routes.transcription_routes.AcceptanceValidator")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_session_not_found_returns_404(
        self, MockTranscriptionRepo, MockValidator, client
    ):
        """Non-existent session returns 404 with SESSION_NOT_FOUND."""
        transcription_id = str(uuid4())

        mock_validator = MockValidator.return_value
        mock_validator.validate = AsyncMock(
            return_value=ValidationResult(
                is_valid=False,
                error_code="SESSION_NOT_FOUND",
                detail="La sesión de transcripción no fue encontrada.",
            )
        )

        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": transcription_id, "text": "Texto"},
        )

        assert response.status_code == 404
        assert response.json()["errorCode"] == "SESSION_NOT_FOUND"


class TestAcceptEndpointEmptyText:
    """Tests for empty transcription text errors (422)."""

    @patch("app.routes.transcription_routes.AcceptanceValidator")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_empty_text_returns_422(
        self, MockTranscriptionRepo, MockValidator, client
    ):
        """Whitespace-only text returns 422 with EMPTY_TRANSCRIPTION."""
        transcription_id = str(uuid4())

        mock_validator = MockValidator.return_value
        mock_validator.validate = AsyncMock(
            return_value=ValidationResult(
                is_valid=False,
                error_code="EMPTY_TRANSCRIPTION",
                detail="El texto de transcripción no puede estar vacío.",
            )
        )

        # Send a non-empty string that passes Pydantic min_length but is whitespace
        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": transcription_id, "text": "   "},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "EMPTY_TRANSCRIPTION"

    def test_pydantic_rejects_empty_string(self, client):
        """Pydantic rejects empty string via min_length=1 before reaching validator."""
        transcription_id = str(uuid4())

        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": transcription_id, "text": ""},
        )

        assert response.status_code == 422


class TestAcceptEndpointNoConfirmedSchema:
    """Tests for missing confirmed schema errors (409)."""

    @patch("app.routes.transcription_routes.AcceptanceValidator")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_no_confirmed_schema_returns_409(
        self, MockTranscriptionRepo, MockValidator, client
    ):
        """No confirmed schema returns 409 with NO_CONFIRMED_SCHEMA."""
        transcription_id = str(uuid4())

        mock_validator = MockValidator.return_value
        mock_validator.validate = AsyncMock(
            return_value=ValidationResult(
                is_valid=False,
                error_code="NO_CONFIRMED_SCHEMA",
                detail="No existe un Esquema_Columnas confirmado.",
            )
        )

        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": transcription_id, "text": "Texto válido"},
        )

        assert response.status_code == 409
        assert response.json()["errorCode"] == "NO_CONFIRMED_SCHEMA"


class TestAcceptEndpointRequestValidation:
    """Tests for request body validation (Pydantic)."""

    def test_missing_transcription_id_returns_422(self, client):
        """Missing transcription_id field returns 422."""
        response = client.post(
            "/api/transcriptions/accept",
            json={"text": "Texto válido"},
        )
        assert response.status_code == 422

    def test_missing_text_returns_422(self, client):
        """Missing text field returns 422."""
        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": str(uuid4())},
        )
        assert response.status_code == 422

    def test_invalid_transcription_id_format_returns_422(self, client):
        """Non-UUID transcription_id returns 422."""
        response = client.post(
            "/api/transcriptions/accept",
            json={"transcription_id": "not-a-uuid", "text": "Texto"},
        )
        assert response.status_code == 422
