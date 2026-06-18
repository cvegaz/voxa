"""Unit tests for GET /api/transcriptions/{id} endpoint."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


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


def _make_session_row(
    session_id=None,
    template_session_id=None,
    status="pending",
    original_text="Hello world",
    final_text=None,
    duration_seconds=5.0,
    created_at=None,
    accepted_at=None,
    discarded_at=None,
):
    """Helper to create a mock database row for a transcription session."""
    return {
        "id": session_id or uuid4(),
        "template_session_id": template_session_id or uuid4(),
        "status": status,
        "original_text": original_text,
        "final_text": final_text,
        "duration_seconds": duration_seconds,
        "created_at": created_at or datetime.now(timezone.utc),
        "accepted_at": accepted_at,
        "discarded_at": discarded_at,
    }


class TestGetTranscriptionSuccess:
    """Tests for successful retrieval of a transcription session."""

    def test_get_existing_session_returns_200(self, client, mock_pool):
        """Retrieving an existing session returns 200 with session data."""
        session_id = uuid4()
        row = _make_session_row(session_id=session_id)

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=row)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.get(f"/api/transcriptions/{session_id}")

        assert response.status_code == 200

    def test_get_session_returns_all_fields(self, client, mock_pool):
        """Response includes all TranscriptionSession fields."""
        session_id = uuid4()
        template_id = uuid4()
        created = datetime.now(timezone.utc)
        row = _make_session_row(
            session_id=session_id,
            template_session_id=template_id,
            status="pending",
            original_text="Test transcription",
            duration_seconds=10.5,
            created_at=created,
        )

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=row)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.get(f"/api/transcriptions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session_id)
        assert data["templateSessionId"] == str(template_id)
        assert data["status"] == "pending"
        assert data["originalText"] == "Test transcription"
        assert data["finalText"] is None
        assert data["durationSeconds"] == 10.5
        assert data["acceptedAt"] is None
        assert data["discardedAt"] is None

    def test_get_accepted_session_includes_final_text(self, client, mock_pool):
        """An accepted session includes final_text and accepted_at."""
        session_id = uuid4()
        accepted_time = datetime.now(timezone.utc)
        row = _make_session_row(
            session_id=session_id,
            status="accepted",
            original_text="Original text",
            final_text="Edited final text",
            accepted_at=accepted_time,
        )

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=row)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.get(f"/api/transcriptions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["finalText"] == "Edited final text"
        assert data["acceptedAt"] is not None


class TestGetTranscriptionNotFound:
    """Tests for session not found cases."""

    def test_get_nonexistent_session_returns_404(self, client, mock_pool):
        """Requesting a non-existent session returns 404."""
        session_id = uuid4()

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.get(f"/api/transcriptions/{session_id}")

        assert response.status_code == 404

    def test_get_not_found_returns_error_code(self, client, mock_pool):
        """404 response contains SESSION_NOT_FOUND error code."""
        session_id = uuid4()

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.get(f"/api/transcriptions/{session_id}")

        assert response.status_code == 404
        assert response.json()["errorCode"] == "SESSION_NOT_FOUND"

    def test_get_invalid_uuid_returns_422(self, client):
        """Requesting with an invalid UUID format returns 422."""
        response = client.get("/api/transcriptions/not-a-valid-uuid")

        assert response.status_code == 422
