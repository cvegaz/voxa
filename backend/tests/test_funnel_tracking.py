"""Tests for the funnel milestones (ADR-0019 §7).

The property that matters most here is **that telemetry can fail without costing
the user anything**. Analytics writes are the classic source of the worst kind of
outage: an optional feature taking down a paid one. Every funnel write in the
routes is wrapped and swallowed, and these tests are what stop that wrapping from
being "cleaned up" later by someone who reads it as sloppy error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    app.state.pool = MagicMock()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def probe():
    with patch("app.routes.transcription_routes.AudioDurationProbe") as cls:
        cls.return_value.measure_seconds = AsyncMock(return_value=5.0)
        yield cls


@pytest.fixture
def whisper():
    with patch("app.routes.transcription_routes.WhisperTranscriptionService") as cls:
        cls.return_value.transcribe = AsyncMock(return_value="Texto de prueba")
        yield cls


@pytest.fixture
def transcription_repo():
    with patch("app.routes.transcription_routes.TranscriptionRepository") as cls:
        cls.return_value.create_session = AsyncMock(return_value=uuid4())
        yield cls


def _active_session():
    session = MagicMock()
    session.id = uuid4()
    session.language = "es"
    return session


def _post_audio(client: TestClient):
    return client.post(
        "/api/transcriptions/transcribe",
        files={"file": ("a.webm", b"\x00\x01\x02", "audio/webm")},
    )


class TestAhaMomentIsRecorded:
    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_a_successful_narration_stamps_the_session(
        self, template_repo_cls, client, probe, whisper, transcription_repo
    ):
        session = _active_session()
        repo = template_repo_cls.return_value
        repo.get_active_session = AsyncMock(return_value=session)
        repo.mark_first_narration = AsyncMock()

        assert _post_audio(client).status_code == 200
        repo.mark_first_narration.assert_awaited_once_with(str(session.id))

    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_a_failed_narration_does_not_stamp_it(
        self, template_repo_cls, client, probe, transcription_repo
    ):
        """The milestone is "reached the aha moment", not "tried to"."""
        from app.services.exceptions import WhisperUnavailableError

        repo = template_repo_cls.return_value
        repo.get_active_session = AsyncMock(return_value=_active_session())
        repo.mark_first_narration = AsyncMock()

        with patch(
            "app.routes.transcription_routes.WhisperTranscriptionService"
        ) as whisper_cls:
            whisper_cls.return_value.transcribe = AsyncMock(
                side_effect=WhisperUnavailableError()
            )
            assert _post_audio(client).status_code == 502

        repo.mark_first_narration.assert_not_awaited()


class TestTelemetryNeverBreaksTheRequest:
    """Analytics is optional; the thing the user asked for is not.

    An unwrapped telemetry write is how an optional feature takes down a paid one.
    These tests exist so the try/except around each funnel write is understood as
    the design and not tidied away as careless error handling.
    """

    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_a_broken_funnel_write_still_returns_the_transcription(
        self, template_repo_cls, client, probe, whisper, transcription_repo
    ):
        repo = template_repo_cls.return_value
        repo.get_active_session = AsyncMock(return_value=_active_session())
        repo.mark_first_narration = AsyncMock(side_effect=RuntimeError("db down"))

        response = _post_audio(client)

        assert response.status_code == 200
        assert response.json()["text"] == "Texto de prueba"

    @patch("app.routes.extraction_routes.TemplateRepository")
    @patch("app.routes.extraction_routes.ExcelExporter")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_a_broken_funnel_write_still_serves_the_download(
        self, extraction_repo_cls, exporter_cls, template_repo_cls, client
    ):
        """The download is the conversion this whole product exists to produce.
        Losing it to a stats write would be the worst possible trade."""
        session_id = uuid4()
        repo = extraction_repo_cls.return_value
        repo.get_export_context = AsyncMock(
            return_value={
                "schema_json": {
                    "columns": [
                        {"index": 1, "name": "Nombre", "data_type": "texto",
                         "example_value": "ej"}
                    ]
                },
                "file_name": "demo.xlsx",
            }
        )
        repo.get_records = AsyncMock(return_value=[])
        exporter_cls.return_value.build = MagicMock(return_value=b"xlsx-bytes")
        template_repo_cls.return_value.mark_downloaded = AsyncMock(
            side_effect=RuntimeError("db down")
        )

        response = client.get(f"/api/extraction/export/{session_id}")

        assert response.status_code == 200
        assert response.content == b"xlsx-bytes"


class TestWallsAreDistinguished:
    """'trial' and 'budget' are different stories and must not be merged.

    A month full of trial walls means healthy visitors to convert. A month full
    of budget walls means the caps are too tight for the traffic that arrived —
    the cue to release the manual headroom.
    """

    @patch("app.routes.extraction_routes.TemplateRepository")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_the_trial_cap_is_recorded_as_trial(
        self, extraction_repo_cls, template_repo_cls, client
    ):
        from app.constants import MAX_ROWS_PER_SESSION

        session_id = uuid4()
        repo = extraction_repo_cls.return_value
        repo.get_session_with_context = AsyncMock(return_value={"status": "finalized"})
        repo.count_records = AsyncMock(return_value=MAX_ROWS_PER_SESSION)
        template_repo_cls.return_value.mark_wall_hit = AsyncMock()

        response = client.post(
            "/api/extraction/process",
            json={"sessionId": str(session_id), "transcribedText": "hola"},
        )

        assert response.json()["errorCode"] == "TRIAL_EXHAUSTED"
        template_repo_cls.return_value.mark_wall_hit.assert_awaited_once_with(
            str(session_id), "trial"
        )

    @patch("app.routes.extraction_routes.TemplateRepository")
    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_the_spend_ceiling_is_recorded_as_budget(
        self, extraction_repo_cls, template_repo_cls, client, stub_usage_ledger
    ):
        from decimal import Decimal

        stub_usage_ledger.spent = Decimal("999")
        session_id = uuid4()
        repo = extraction_repo_cls.return_value
        repo.get_session_with_context = AsyncMock(return_value={"status": "confirmed"})
        template_repo_cls.return_value.mark_wall_hit = AsyncMock()

        response = client.post(
            "/api/extraction/process",
            json={"sessionId": str(session_id), "transcribedText": "hola"},
        )

        assert response.status_code == 429
        assert response.json()["errorCode"] == "DEMO_BUDGET_EXHAUSTED"
        template_repo_cls.return_value.mark_wall_hit.assert_awaited_once_with(
            str(session_id), "budget"
        )
