"""Unit tests for POST /api/transcriptions/transcribe endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.template_models import ColumnDef, ColumnSchema, TemplateSession
from app.models.transcription_models import ErrorResponse


def _make_active_session() -> TemplateSession:
    """Create a mock active (confirmed) template session."""
    from datetime import datetime, timezone

    return TemplateSession(
        id=uuid4(),
        status="confirmed",
        schema_json=ColumnSchema(
            columns=[ColumnDef(index=1, name="Col1", data_type="texto", example_value="ej")]
        ),
        dataframe_json="[]",
        enriched_context="context",
        file_name="test.xlsx",
        column_count=1,
        created_at=datetime.now(timezone.utc),
        confirmed_at=datetime.now(timezone.utc),
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


class TestTranscribeEndpointSuccess:
    """Tests for successful transcription."""

    @patch("app.routes.transcription_routes.WhisperTranscriptionService")
    @patch("app.routes.transcription_routes.TemplateRepository")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_valid_audio_returns_200(
        self, mock_trans_repo_cls, mock_tmpl_repo_cls, mock_whisper_cls, client, mock_pool
    ):
        """Valid audio file returns 200 with transcription_id and text."""
        transcription_id = uuid4()
        active_session = _make_active_session()

        # Mock TemplateRepository.get_active_session
        mock_tmpl_repo = MagicMock()
        mock_tmpl_repo.get_active_session = AsyncMock(return_value=active_session)
        mock_tmpl_repo_cls.return_value = mock_tmpl_repo

        # Mock WhisperTranscriptionService.transcribe
        mock_whisper = MagicMock()
        mock_whisper.transcribe = AsyncMock(return_value="Texto transcrito de prueba")
        mock_whisper_cls.return_value = mock_whisper

        # Mock TranscriptionRepository.create_session
        mock_trans_repo = MagicMock()
        mock_trans_repo.create_session = AsyncMock(return_value=transcription_id)
        mock_trans_repo_cls.return_value = mock_trans_repo

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02\x03", "audio/webm")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transcription_id"] == str(transcription_id)
        assert data["text"] == "Texto transcrito de prueba"

    @patch("app.routes.transcription_routes.WhisperTranscriptionService")
    @patch("app.routes.transcription_routes.TemplateRepository")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_transcribe_calls_create_session_with_correct_params(
        self, mock_trans_repo_cls, mock_tmpl_repo_cls, mock_whisper_cls, client, mock_pool
    ):
        """create_session is called with template_session_id, text, and duration."""
        transcription_id = uuid4()
        active_session = _make_active_session()

        mock_tmpl_repo = MagicMock()
        mock_tmpl_repo.get_active_session = AsyncMock(return_value=active_session)
        mock_tmpl_repo_cls.return_value = mock_tmpl_repo

        mock_whisper = MagicMock()
        mock_whisper.transcribe = AsyncMock(return_value="Hola mundo")
        mock_whisper_cls.return_value = mock_whisper

        mock_trans_repo = MagicMock()
        mock_trans_repo.create_session = AsyncMock(return_value=transcription_id)
        mock_trans_repo_cls.return_value = mock_trans_repo

        client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02\x03", "audio/webm")},
            data={"duration": "10.5"},
        )

        mock_trans_repo.create_session.assert_called_once_with(
            template_session_id=active_session.id,
            text="Hola mundo",
            duration_seconds=10.5,
        )


class TestTranscribeEndpointValidationErrors:
    """Tests for audio validation failures returning 422."""

    def test_empty_audio_file_returns_422(self, client):
        """Empty audio file returns 422 with EMPTY_AUDIO_FILE error."""
        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"", "audio/webm")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 422
        data = response.json()["detail"]
        assert data["error_code"] == "EMPTY_AUDIO_FILE"

    def test_unsupported_mime_type_returns_422(self, client):
        """Unsupported MIME type returns 422 with UNSUPPORTED_AUDIO_FORMAT error."""
        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.txt", b"\x00\x01\x02", "text/plain")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 422
        data = response.json()["detail"]
        assert data["error_code"] == "UNSUPPORTED_AUDIO_FORMAT"

    def test_duration_too_short_returns_422(self, client):
        """Duration < 1.0s returns 422 with AUDIO_TOO_SHORT error."""
        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "0.5"},
        )

        assert response.status_code == 422
        data = response.json()["detail"]
        assert data["error_code"] == "AUDIO_TOO_SHORT"

    def test_duration_too_long_returns_422(self, client):
        """Duration > 30.0s returns 422 with AUDIO_TOO_LONG error."""
        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "31.0"},
        )

        assert response.status_code == 422
        data = response.json()["detail"]
        assert data["error_code"] == "AUDIO_TOO_LONG"


class TestTranscribeEndpointNoActiveSession:
    """Tests for missing confirmed template session."""

    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_no_confirmed_schema_returns_409(self, mock_tmpl_repo_cls, client, mock_pool):
        """No active template session returns 409 with NO_CONFIRMED_SCHEMA."""
        mock_tmpl_repo = MagicMock()
        mock_tmpl_repo.get_active_session = AsyncMock(return_value=None)
        mock_tmpl_repo_cls.return_value = mock_tmpl_repo

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 409
        data = response.json()["detail"]
        assert data["error_code"] == "NO_CONFIRMED_SCHEMA"


class TestTranscribeEndpointWhisperErrors:
    """Tests for Whisper API error handling."""

    @patch("app.routes.transcription_routes.WhisperTranscriptionService")
    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_whisper_unavailable_returns_502(
        self, mock_tmpl_repo_cls, mock_whisper_cls, client, mock_pool
    ):
        """WhisperUnavailableError returns 502 with WHISPER_UNAVAILABLE."""
        from app.services.exceptions import WhisperUnavailableError

        active_session = _make_active_session()
        mock_tmpl_repo = MagicMock()
        mock_tmpl_repo.get_active_session = AsyncMock(return_value=active_session)
        mock_tmpl_repo_cls.return_value = mock_tmpl_repo

        mock_whisper = MagicMock()
        mock_whisper.transcribe = AsyncMock(side_effect=WhisperUnavailableError())
        mock_whisper_cls.return_value = mock_whisper

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 502
        data = response.json()["detail"]
        assert data["error_code"] == "WHISPER_UNAVAILABLE"

    @patch("app.routes.transcription_routes.WhisperTranscriptionService")
    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_whisper_empty_response_returns_502(
        self, mock_tmpl_repo_cls, mock_whisper_cls, client, mock_pool
    ):
        """WhisperEmptyResponseError returns 502 with WHISPER_EMPTY_RESPONSE."""
        from app.services.exceptions import WhisperEmptyResponseError

        active_session = _make_active_session()
        mock_tmpl_repo = MagicMock()
        mock_tmpl_repo.get_active_session = AsyncMock(return_value=active_session)
        mock_tmpl_repo_cls.return_value = mock_tmpl_repo

        mock_whisper = MagicMock()
        mock_whisper.transcribe = AsyncMock(side_effect=WhisperEmptyResponseError())
        mock_whisper_cls.return_value = mock_whisper

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 502
        data = response.json()["detail"]
        assert data["error_code"] == "WHISPER_EMPTY_RESPONSE"

    @patch("app.routes.transcription_routes.WhisperTranscriptionService")
    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_whisper_no_speech_returns_422(
        self, mock_tmpl_repo_cls, mock_whisper_cls, client, mock_pool
    ):
        """WhisperNoSpeechError returns 422 with WHISPER_NO_SPEECH."""
        from app.services.exceptions import WhisperNoSpeechError

        active_session = _make_active_session()
        mock_tmpl_repo = MagicMock()
        mock_tmpl_repo.get_active_session = AsyncMock(return_value=active_session)
        mock_tmpl_repo_cls.return_value = mock_tmpl_repo

        mock_whisper = MagicMock()
        mock_whisper.transcribe = AsyncMock(side_effect=WhisperNoSpeechError())
        mock_whisper_cls.return_value = mock_whisper

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 422
        data = response.json()["detail"]
        assert data["error_code"] == "WHISPER_NO_SPEECH"
