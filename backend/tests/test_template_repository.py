"""Unit tests for TemplateRepository."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from app.models.template_models import ColumnDef, ColumnSchema, TemplateSession
from app.repositories.template_repository import TemplateRepository


@pytest.fixture
def sample_schema() -> ColumnSchema:
    """Create a sample ColumnSchema for testing."""
    return ColumnSchema(
        columns=[
            ColumnDef(index=1, name="Nombre", data_type="texto", example_value="Juan"),
            ColumnDef(index=2, name="Edad", data_type="número entero", example_value="30"),
            ColumnDef(index=3, name="Fecha", data_type="fecha DD/MM/YYYY", example_value="15/03/2024"),
        ]
    )


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
async def test_create_session_returns_session_id(mock_pool, sample_schema):
    """Test that create_session persists a session and returns the UUID."""
    pool, conn = mock_pool
    session_id = uuid4()
    conn.fetchrow.return_value = {"id": session_id}

    repo = TemplateRepository(pool)
    result = await repo.create_session(
        schema=sample_schema,
        dataframe_json='[{"Nombre": "Juan", "Edad": 30}]',
        file_name="test.xlsx",
    )

    assert result == str(session_id)
    conn.fetchrow.assert_called_once()
    call_args = conn.fetchrow.call_args
    # Verify the SQL contains INSERT and pending status
    assert "INSERT INTO template_sessions" in call_args[0][0]
    assert "'pending'" in call_args[0][0]
    # Verify schema_json is passed as serialized JSON
    schema_arg = call_args[0][1]
    parsed = json.loads(schema_arg)
    assert len(parsed["columns"]) == 3
    assert parsed["columns"][0]["name"] == "Nombre"


@pytest.mark.asyncio
async def test_create_session_passes_correct_column_count(mock_pool, sample_schema):
    """Test that create_session calculates column_count from schema."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = {"id": uuid4()}

    repo = TemplateRepository(pool)
    await repo.create_session(
        schema=sample_schema,
        dataframe_json="[]",
        file_name="test.xlsx",
    )

    call_args = conn.fetchrow.call_args
    # column_count is the 4th positional arg after SQL
    column_count_arg = call_args[0][4]
    assert column_count_arg == 3


@pytest.mark.asyncio
async def test_confirm_session_updates_status(mock_pool):
    """Test that confirm_session updates status to confirmed with enriched context."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 1"
    session_id = str(uuid4())

    repo = TemplateRepository(pool)
    await repo.confirm_session(
        session_id=session_id,
        enriched_context="This is an enriched context about the data.",
        user_context="Original user context.",
    )

    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    sql = call_args[0][0]
    assert "SET status = 'confirmed'" in sql
    assert "enriched_context" in sql
    assert "confirmed_at" in sql
    assert "AND status = 'pending'" in sql


@pytest.mark.asyncio
async def test_confirm_session_raises_on_not_found(mock_pool):
    """Test that confirm_session raises ValueError if session not found."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 0"
    session_id = str(uuid4())

    repo = TemplateRepository(pool)
    with pytest.raises(ValueError, match="not found or not in 'pending' status"):
        await repo.confirm_session(
            session_id=session_id,
            enriched_context="Some context",
        )


@pytest.mark.asyncio
async def test_get_active_session_returns_latest_confirmed(mock_pool, sample_schema):
    """Test that get_active_session returns the most recent confirmed session."""
    pool, conn = mock_pool
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    schema_data = sample_schema.model_dump()

    conn.fetchrow.return_value = {
        "id": session_id,
        "status": "confirmed",
        "schema_json": schema_data,
        "dataframe_json": [{"Nombre": "Juan"}],
        "user_context": "User context",
        "enriched_context": "Enriched context",
        "file_name": "data.xlsx",
        "column_count": 3,
        "created_at": now,
        "confirmed_at": now,
        "replaced_at": None,
    }

    repo = TemplateRepository(pool)
    session = await repo.get_active_session()

    assert session is not None
    assert session.id == session_id
    assert session.status == "confirmed"
    assert session.enriched_context == "Enriched context"
    assert len(session.column_schema.columns) == 3
    # Verify query filters by confirmed status and orders by confirmed_at DESC
    call_args = conn.fetchrow.call_args
    sql = call_args[0][0]
    assert "WHERE status = 'confirmed'" in sql
    assert "ORDER BY confirmed_at DESC" in sql
    assert "LIMIT 1" in sql


@pytest.mark.asyncio
async def test_get_active_session_returns_none_when_no_confirmed(mock_pool):
    """Test that get_active_session returns None if no confirmed sessions exist."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = None

    repo = TemplateRepository(pool)
    session = await repo.get_active_session()

    assert session is None


@pytest.mark.asyncio
async def test_replace_previous_sessions_marks_all(mock_pool):
    """Test that replace_previous_sessions marks pending and confirmed as replaced."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 3"

    repo = TemplateRepository(pool)
    count = await repo.replace_previous_sessions()

    assert count == 3
    call_args = conn.execute.call_args
    sql = call_args[0][0]
    assert "SET status = 'replaced'" in sql
    assert "replaced_at" in sql
    assert "WHERE status IN ('pending', 'confirmed')" in sql


@pytest.mark.asyncio
async def test_replace_previous_sessions_returns_zero_when_none(mock_pool):
    """Test that replace_previous_sessions returns 0 when no sessions to replace."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 0"

    repo = TemplateRepository(pool)
    count = await repo.replace_previous_sessions()

    assert count == 0


@pytest.mark.asyncio
async def test_get_session_by_id(mock_pool, sample_schema):
    """Test retrieval of a specific session by ID."""
    pool, conn = mock_pool
    session_id = uuid4()
    now = datetime.now(timezone.utc)

    conn.fetchrow.return_value = {
        "id": session_id,
        "status": "pending",
        "schema_json": sample_schema.model_dump(),
        "dataframe_json": "[]",
        "user_context": None,
        "enriched_context": None,
        "file_name": "test.xlsx",
        "column_count": 3,
        "created_at": now,
        "confirmed_at": None,
        "replaced_at": None,
    }

    repo = TemplateRepository(pool)
    session = await repo.get_session_by_id(str(session_id))

    assert session is not None
    assert session.id == session_id
    assert session.status == "pending"


@pytest.mark.asyncio
async def test_mark_session_replaced_success(mock_pool):
    """Test marking a specific session as replaced."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 1"

    repo = TemplateRepository(pool)
    result = await repo.mark_session_replaced(str(uuid4()))

    assert result is True


@pytest.mark.asyncio
async def test_mark_session_replaced_not_found(mock_pool):
    """Test marking a non-existent session returns False."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 0"

    repo = TemplateRepository(pool)
    result = await repo.mark_session_replaced(str(uuid4()))

    assert result is False
