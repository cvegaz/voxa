"""Unit tests for POST /api/extraction/finalize/{session_id} endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    return MagicMock()


@pytest.fixture
def client(mock_pool):
    """Create a test client with mocked database pool."""
    app.state.pool = mock_pool
    return TestClient(app, raise_server_exceptions=False)


class TestFinalizeSession:
    """Tests for finalizing a capture session."""

    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_finalize_confirmed_session_returns_finalized(self, MockRepo, client):
        """A confirmed session is marked finalized and the count is returned."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_status = AsyncMock(return_value="confirmed")
        mock_repo.mark_finalized = AsyncMock()
        mock_repo.count_records = AsyncMock(return_value=3)

        response = client.post(f"/api/extraction/finalize/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "finalized"
        assert data["totalRows"] == 3
        mock_repo.mark_finalized.assert_awaited_once_with(session_id)

    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_finalize_is_idempotent(self, MockRepo, client):
        """Finalizing an already-finalized session is a no-op that still succeeds."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_status = AsyncMock(return_value="finalized")
        mock_repo.mark_finalized = AsyncMock()
        mock_repo.count_records = AsyncMock(return_value=5)

        response = client.post(f"/api/extraction/finalize/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "finalized"
        assert data["totalRows"] == 5
        # No redundant write when already finalized.
        mock_repo.mark_finalized.assert_not_called()

    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_finalize_missing_session_returns_404(self, MockRepo, client):
        """An unknown session returns 404 SESSION_NOT_FOUND."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_status = AsyncMock(return_value=None)

        response = client.post(f"/api/extraction/finalize/{session_id}")

        assert response.status_code == 404
        assert response.json()["errorCode"] == "SESSION_NOT_FOUND"

    @patch("app.routes.extraction_routes.ExtractionRepository")
    def test_finalize_unconfirmed_session_returns_422(self, MockRepo, client):
        """A pending session cannot be finalized (422 SESSION_NOT_CONFIRMED)."""
        session_id = str(uuid4())

        mock_repo = MockRepo.return_value
        mock_repo.get_status = AsyncMock(return_value="pending")
        mock_repo.mark_finalized = AsyncMock()

        response = client.post(f"/api/extraction/finalize/{session_id}")

        assert response.status_code == 422
        assert response.json()["errorCode"] == "SESSION_NOT_CONFIRMED"
        mock_repo.mark_finalized.assert_not_called()

    def test_finalize_invalid_uuid_returns_422(self, client):
        """A non-UUID session id is rejected by FastAPI path validation."""
        response = client.post("/api/extraction/finalize/not-a-uuid")
        assert response.status_code == 422
