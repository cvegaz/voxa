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


@pytest.fixture(autouse=True)
def stub_probe():
    """Stub the duration probe for every test in this module.

    ADR-0019 made the endpoint **measure** the uploaded audio instead of believing
    the client's ``duration`` field. Without this stub each endpoint test would
    shell out to ``ffprobe`` on fake bytes — an environment dependency the suite
    forbids (ADR-0009: tests run offline and must not require ffmpeg).

    ``seconds`` is what the server believes the file *really* is. Set it to an
    exception instance to simulate an unreadable file.
    """

    class _StubProbe:
        seconds: object = 5.0

        def __init__(self, *args, **kwargs):
            pass

        async def measure_seconds(self, data: bytes, suffix: str = "") -> float:
            if isinstance(_StubProbe.seconds, Exception):
                raise _StubProbe.seconds
            return _StubProbe.seconds

    with patch("app.routes.transcription_routes.AudioDurationProbe", _StubProbe):
        yield _StubProbe


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
        assert data["transcriptionId"] == str(transcription_id)
        assert data["text"] == "Texto transcrito de prueba"

    @patch("app.routes.transcription_routes.WhisperTranscriptionService")
    @patch("app.routes.transcription_routes.TemplateRepository")
    @patch("app.routes.transcription_routes.TranscriptionRepository")
    def test_transcribe_persists_the_measured_duration_not_the_claimed_one(
        self,
        mock_trans_repo_cls,
        mock_tmpl_repo_cls,
        mock_whisper_cls,
        client,
        mock_pool,
        stub_probe,
    ):
        """create_session stores the MEASURED duration (ADR-0019).

        The client claims 2.0 s while the file really is 10.5 s. What gets persisted
        must be 10.5 — it is the duration the OpenAI cost was actually incurred on,
        and therefore the only one worth keeping for the usage ledger.
        """
        transcription_id = uuid4()
        active_session = _make_active_session()
        stub_probe.seconds = 10.5

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
            data={"duration": "2.0"},
        )

        mock_trans_repo.create_session.assert_called_once_with(
            template_session_id=active_session.id,
            text="Hola mundo",
            duration_seconds=10.5,
        )

    def test_duration_field_is_optional(self, client, stub_probe):
        """The client may omit ``duration`` entirely — it is no longer a control.

        Kept as an accepted field for backward compatibility, but a request without
        it must not be rejected as malformed.
        """
        stub_probe.seconds = 300.0  # rejected on its own merits, not for a missing field

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02\x03", "audio/webm")},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "AUDIO_TOO_LONG"


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
        assert response.json()["errorCode"] == "EMPTY_AUDIO_FILE"

    def test_unsupported_mime_type_returns_422(self, client):
        """Unsupported MIME type returns 422 with UNSUPPORTED_AUDIO_FORMAT error."""
        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.txt", b"\x00\x01\x02", "text/plain")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "UNSUPPORTED_AUDIO_FORMAT"

    def test_duration_too_short_returns_422(self, client, stub_probe):
        """A file measuring < 1.0s returns 422 with AUDIO_TOO_SHORT."""
        stub_probe.seconds = 0.5

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "0.5"},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "AUDIO_TOO_SHORT"

    def test_duration_too_long_returns_422(self, client, stub_probe):
        """A file measuring above the max (default 20.0s) returns 422 AUDIO_TOO_LONG."""
        stub_probe.seconds = 31.0

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "31.0"},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "AUDIO_TOO_LONG"


class TestTranscribeEndpointTrustBoundary:
    """The regression suite for ADR-0019 §1.

    ADR-0014 decided the recording cap must hold against "an upload (or a tampered
    client)". The implementation validated the client's own ``duration`` form field,
    so the cap was fiction: a request could claim 5 s while carrying ten minutes of
    audio and OpenAI billed the ten. These tests encode the boundary so it cannot
    silently regress.
    """

    def test_long_audio_rejected_even_when_client_claims_it_is_short(
        self, client, stub_probe
    ):
        """The lie is ignored: 5 s claimed, 10 minutes measured, request rejected."""
        stub_probe.seconds = 600.0

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "5.0"},  # the tampered claim
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "AUDIO_TOO_LONG"

    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_short_audio_accepted_even_when_client_claims_it_is_long(
        self, mock_tmpl_repo_cls, client, stub_probe
    ):
        """The boundary cuts both ways: the measurement decides, not the claim.

        A client reporting an over-cap duration for a file that is actually fine must
        not be rejected — otherwise the field would still be a control, merely an
        inverted one. Reaching the session check (409) proves audio validation passed.
        """
        stub_probe.seconds = 4.0

        mock_tmpl_repo = MagicMock()
        mock_tmpl_repo.get_active_session = AsyncMock(return_value=None)
        mock_tmpl_repo_cls.return_value = mock_tmpl_repo

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "999.0"},
        )

        assert response.status_code == 409
        assert response.json()["errorCode"] == "NO_CONFIRMED_SCHEMA"

    def test_unreadable_audio_returns_422(self, client, stub_probe):
        """We fail CLOSED: a file we cannot measure is never sent to Whisper."""
        from app.services.exceptions import AudioUnreadableError

        stub_probe.seconds = AudioUnreadableError()

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", b"\x00\x01\x02", "audio/webm")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "AUDIO_UNREADABLE"

    def test_oversized_audio_rejected_before_the_probe_runs(self, client, stub_probe):
        """The byte ceiling is a pre-filter: no temp file, no subprocess, no cost."""
        probed: list[bytes] = []

        async def _record(self, data, suffix=""):
            probed.append(data)
            return 5.0

        stub_probe.measure_seconds = _record

        from app.constants import MAX_AUDIO_BYTES

        oversized = b"\x00" * (MAX_AUDIO_BYTES + 1)
        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("audio.webm", oversized, "audio/webm")},
            data={"duration": "5.0"},
        )

        assert response.status_code == 422
        assert response.json()["errorCode"] == "AUDIO_TOO_LARGE"
        assert probed == [], "the probe must not run on an already-rejected upload"


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
        assert response.json()["errorCode"] == "NO_CONFIRMED_SCHEMA"


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
        assert response.json()["errorCode"] == "WHISPER_UNAVAILABLE"

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
        assert response.json()["errorCode"] == "WHISPER_EMPTY_RESPONSE"

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
        assert response.json()["errorCode"] == "WHISPER_NO_SPEECH"
