"""Tests for POST /api/transcriptions/reset endpoint."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_pool():
    """Mock the database pool on app state."""
    pool = AsyncMock()
    app.state.pool = pool
    return pool


@pytest.mark.asyncio
async def test_reset_success(mock_pool):
    """Reset endpoint returns status 'reset' when session is discarded successfully."""
    transcription_id = uuid4()

    with patch(
        "app.routes.transcription_routes.TranscriptionRepository"
    ) as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.discard_session = AsyncMock(return_value=None)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/transcriptions/reset",
                json={"transcription_id": str(transcription_id)},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reset"
    mock_repo_instance.discard_session.assert_awaited_once_with(transcription_id)


@pytest.mark.asyncio
async def test_reset_session_not_found(mock_pool):
    """Reset endpoint returns 404 when session is not found or not pending."""
    transcription_id = uuid4()

    with patch(
        "app.routes.transcription_routes.TranscriptionRepository"
    ) as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.discard_session = AsyncMock(
            side_effect=ValueError("session not found")
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/transcriptions/reset",
                json={"transcription_id": str(transcription_id)},
            )

    assert response.status_code == 404
    data = response.json()
    assert data["errorCode"] == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_reset_invalid_uuid(mock_pool):
    """Reset endpoint returns 422 when transcription_id is not a valid UUID."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/transcriptions/reset",
            json={"transcription_id": "not-a-uuid"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reset_missing_transcription_id(mock_pool):
    """Reset endpoint returns 422 when transcription_id is missing from body."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/transcriptions/reset",
            json={},
        )

    assert response.status_code == 422
