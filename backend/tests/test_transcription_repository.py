"""Unit tests for TranscriptionRepository."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.transcription_models import TranscriptionSession
from app.repositories.transcription_repository import TranscriptionRepository


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    pool = MagicMock()
    conn = AsyncMock()

    # asyncpg pool.acquire() returns an async context manager
    acm = AsyncMock()
    acm.__aenter__.return_value = conn
    acm.__aexit__.return_value = False
    pool.acquire.return_value = acm

    return pool, conn


@pytest.mark.asyncio
async def test_create_session_returns_uuid(mock_pool):
    """Test that create_session inserts a row and returns the generated UUID."""
    pool, conn = mock_pool
    session_id = uuid4()
    template_session_id = uuid4()
    conn.fetchrow.return_value = {"id": session_id}

    repo = TranscriptionRepository(pool)
    result = await repo.create_session(
        template_session_id=template_session_id,
        text="Hello world transcription",
        duration_seconds=5.5,
    )

    assert result == session_id
    conn.fetchrow.assert_called_once()
    call_args = conn.fetchrow.call_args
    sql = call_args[0][0]
    assert "INSERT INTO transcription_sessions" in sql
    assert "'pending'" in sql
    # Verify positional parameters
    assert call_args[0][1] == template_session_id
    assert call_args[0][2] == "Hello world transcription"
    assert call_args[0][3] == 5.5


@pytest.mark.asyncio
async def test_create_session_stores_original_text(mock_pool):
    """Test that create_session stores the original transcribed text."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = {"id": uuid4()}

    repo = TranscriptionRepository(pool)
    await repo.create_session(
        template_session_id=uuid4(),
        text="Texto de prueba con acentos y ñ",
        duration_seconds=10.0,
    )

    call_args = conn.fetchrow.call_args
    assert call_args[0][2] == "Texto de prueba con acentos y ñ"


@pytest.mark.asyncio
async def test_accept_session_updates_status_and_text(mock_pool):
    """Test that accept_session sets status to accepted with final text and timestamp."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 1"
    transcription_id = uuid4()

    repo = TranscriptionRepository(pool)
    await repo.accept_session(
        transcription_id=transcription_id,
        final_text="Edited final text",
    )

    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    sql = call_args[0][0]
    assert "SET status = 'accepted'" in sql
    assert "final_text" in sql
    assert "accepted_at" in sql
    assert "AND status = 'pending'" in sql
    # Verify final_text parameter
    assert call_args[0][1] == "Edited final text"
    # Verify accepted_at is a datetime
    assert isinstance(call_args[0][2], datetime)
    # Verify transcription_id parameter
    assert call_args[0][3] == transcription_id


@pytest.mark.asyncio
async def test_accept_session_raises_on_not_found(mock_pool):
    """Test that accept_session raises ValueError if session not found or not pending."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 0"

    repo = TranscriptionRepository(pool)
    with pytest.raises(ValueError, match="not found or not in 'pending' status"):
        await repo.accept_session(
            transcription_id=uuid4(),
            final_text="Some text",
        )


@pytest.mark.asyncio
async def test_discard_session_updates_status(mock_pool):
    """Test that discard_session sets status to discarded with timestamp."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 1"
    transcription_id = uuid4()

    repo = TranscriptionRepository(pool)
    await repo.discard_session(transcription_id=transcription_id)

    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    sql = call_args[0][0]
    assert "SET status = 'discarded'" in sql
    assert "discarded_at" in sql
    assert "AND status = 'pending'" in sql
    # Verify discarded_at is a datetime
    assert isinstance(call_args[0][1], datetime)
    # Verify transcription_id parameter
    assert call_args[0][2] == transcription_id


@pytest.mark.asyncio
async def test_discard_session_raises_on_not_found(mock_pool):
    """Test that discard_session raises ValueError if session not found or not pending."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 0"

    repo = TranscriptionRepository(pool)
    with pytest.raises(ValueError, match="not found or not in 'pending' status"):
        await repo.discard_session(transcription_id=uuid4())


@pytest.mark.asyncio
async def test_get_session_returns_session(mock_pool):
    """Test that get_session returns a TranscriptionSession when found."""
    pool, conn = mock_pool
    session_id = uuid4()
    template_session_id = uuid4()
    now = datetime.now(timezone.utc)

    conn.fetchrow.return_value = {
        "id": session_id,
        "template_session_id": template_session_id,
        "status": "pending",
        "original_text": "Original transcription",
        "final_text": None,
        "duration_seconds": Decimal("15.50"),
        "created_at": now,
        "accepted_at": None,
        "discarded_at": None,
    }

    repo = TranscriptionRepository(pool)
    session = await repo.get_session(transcription_id=session_id)

    assert session is not None
    assert isinstance(session, TranscriptionSession)
    assert session.id == session_id
    assert session.template_session_id == template_session_id
    assert session.status == "pending"
    assert session.original_text == "Original transcription"
    assert session.final_text is None
    assert session.duration_seconds == 15.50
    assert session.created_at == now
    assert session.accepted_at is None
    assert session.discarded_at is None


@pytest.mark.asyncio
async def test_get_session_returns_none_when_not_found(mock_pool):
    """Test that get_session returns None for non-existent session."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = None

    repo = TranscriptionRepository(pool)
    session = await repo.get_session(transcription_id=uuid4())

    assert session is None


@pytest.mark.asyncio
async def test_get_session_with_accepted_status(mock_pool):
    """Test get_session correctly maps an accepted session with final_text."""
    pool, conn = mock_pool
    session_id = uuid4()
    template_session_id = uuid4()
    now = datetime.now(timezone.utc)

    conn.fetchrow.return_value = {
        "id": session_id,
        "template_session_id": template_session_id,
        "status": "accepted",
        "original_text": "Original text",
        "final_text": "Edited final text",
        "duration_seconds": Decimal("8.25"),
        "created_at": now,
        "accepted_at": now,
        "discarded_at": None,
    }

    repo = TranscriptionRepository(pool)
    session = await repo.get_session(transcription_id=session_id)

    assert session is not None
    assert session.status == "accepted"
    assert session.final_text == "Edited final text"
    assert session.accepted_at == now
