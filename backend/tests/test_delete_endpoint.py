"""Unit tests for DELETE /api/templates/{session_id} endpoint."""

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


class TestDeleteEndpointSuccess:
    """Tests for successful session deletion."""

    def test_delete_existing_session_returns_204(self, client, mock_pool):
        """Deleting an existing session returns 204 No Content."""
        session_id = str(uuid4())

        mock_conn = AsyncMock()
        # mark_session_replaced returns "UPDATE 1" when found
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.delete(f"/api/templates/{session_id}")

        assert response.status_code == 204
        assert response.content == b""

    def test_delete_returns_no_body(self, client, mock_pool):
        """Successful delete response has no body content."""
        session_id = str(uuid4())

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.delete(f"/api/templates/{session_id}")

        assert response.status_code == 204
        assert len(response.content) == 0


class TestDeleteEndpointNotFound:
    """Tests for session not found cases."""

    def test_delete_nonexistent_session_returns_404(self, client, mock_pool):
        """Deleting a non-existent session returns 404."""
        session_id = str(uuid4())

        mock_conn = AsyncMock()
        # mark_session_replaced returns "UPDATE 0" when not found
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.delete(f"/api/templates/{session_id}")

        assert response.status_code == 404

    def test_delete_not_found_returns_error_code(self, client, mock_pool):
        """404 response contains SESSION_NOT_FOUND error code."""
        session_id = str(uuid4())

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        response = client.delete(f"/api/templates/{session_id}")

        assert response.status_code == 404
        assert response.json()["errorCode"] == "SESSION_NOT_FOUND"

    def test_delete_invalid_uuid_returns_422(self, client):
        """Deleting with an invalid UUID format returns 422."""
        response = client.delete("/api/templates/not-a-valid-uuid")

        assert response.status_code == 422
