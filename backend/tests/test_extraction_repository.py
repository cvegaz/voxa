"""Unit tests for ExtractionRepository."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.repositories.extraction_repository import ExtractionRepository


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
async def test_save_extraction_returns_id(mock_pool):
    """Test that save_extraction persists a record and returns the UUID."""
    pool, conn = mock_pool
    extraction_id = uuid4()
    conn.fetchrow.return_value = {"id": extraction_id}

    repo = ExtractionRepository(pool)
    session_id = str(uuid4())
    record = {"Nombre": "Juan", "Edad": "30", "Fecha": "15/03/2024"}

    result = await repo.save_extraction(
        session_id=session_id,
        record=record,
        row_number=4,
        transcribed_text="El nombre es Juan, tiene 30 años.",
    )

    assert result == str(extraction_id)
    conn.fetchrow.assert_called_once()
    call_args = conn.fetchrow.call_args
    sql = call_args[0][0]
    assert "INSERT INTO extraction_records" in sql
    assert "'completed'" in sql


@pytest.mark.asyncio
async def test_save_extraction_passes_correct_params(mock_pool):
    """Test that save_extraction passes correct parameters to the query."""
    pool, conn = mock_pool
    extraction_id = uuid4()
    conn.fetchrow.return_value = {"id": extraction_id}

    repo = ExtractionRepository(pool)
    session_id = str(uuid4())
    record = {"Nombre": "Maria", "Edad": "25"}

    await repo.save_extraction(
        session_id=session_id,
        record=record,
        row_number=5,
        transcribed_text="Maria tiene 25 años.",
    )

    call_args = conn.fetchrow.call_args
    # Positional args: SQL, session_id (UUID), row_number, record_json, transcribed_text
    assert call_args[0][1] == UUID(session_id)
    assert call_args[0][2] == 5
    assert json.loads(call_args[0][3]) == record
    assert call_args[0][4] == "Maria tiene 25 años."


@pytest.mark.asyncio
async def test_get_records_returns_ordered_list(mock_pool):
    """Test that get_records returns records ordered by row_number ASC."""
    pool, conn = mock_pool
    session_id = str(uuid4())
    now = datetime.now(timezone.utc)

    conn.fetch.return_value = [
        {
            "id": uuid4(),
            "session_id": UUID(session_id),
            "row_number": 4,
            "record_json": {"Nombre": "Juan"},
            "transcribed_text": "Juan...",
            "status": "completed",
            "error_message": None,
            "created_at": now,
        },
        {
            "id": uuid4(),
            "session_id": UUID(session_id),
            "row_number": 5,
            "record_json": {"Nombre": "Maria"},
            "transcribed_text": "Maria...",
            "status": "completed",
            "error_message": None,
            "created_at": now,
        },
    ]

    repo = ExtractionRepository(pool)
    records = await repo.get_records(session_id)

    assert len(records) == 2
    assert records[0]["row_number"] == 4
    assert records[1]["row_number"] == 5
    assert records[0]["record_json"] == {"Nombre": "Juan"}
    assert records[1]["record_json"] == {"Nombre": "Maria"}

    # Verify ORDER BY row_number ASC in SQL
    call_args = conn.fetch.call_args
    sql = call_args[0][0]
    assert "ORDER BY row_number ASC" in sql


@pytest.mark.asyncio
async def test_get_records_handles_string_json(mock_pool):
    """Test that get_records handles record_json as a string (parsing it)."""
    pool, conn = mock_pool
    session_id = str(uuid4())
    now = datetime.now(timezone.utc)

    conn.fetch.return_value = [
        {
            "id": uuid4(),
            "session_id": UUID(session_id),
            "row_number": 4,
            "record_json": '{"Nombre": "Carlos"}',
            "transcribed_text": "Carlos...",
            "status": "completed",
            "error_message": None,
            "created_at": now,
        },
    ]

    repo = ExtractionRepository(pool)
    records = await repo.get_records(session_id)

    assert len(records) == 1
    assert records[0]["record_json"] == {"Nombre": "Carlos"}


@pytest.mark.asyncio
async def test_get_records_returns_empty_list(mock_pool):
    """Test that get_records returns an empty list when no records exist."""
    pool, conn = mock_pool
    conn.fetch.return_value = []

    repo = ExtractionRepository(pool)
    records = await repo.get_records(str(uuid4()))

    assert records == []


@pytest.mark.asyncio
async def test_get_session_with_context_returns_dict(mock_pool):
    """Test that get_session_with_context returns session data as a dict."""
    pool, conn = mock_pool
    session_id = uuid4()
    schema_data = {"columns": [{"index": 1, "name": "Nombre", "data_type": "texto", "example_value": "Juan"}]}

    conn.fetchrow.return_value = {
        "id": session_id,
        "schema_json": schema_data,
        "enriched_context": "Context about the data extraction.",
        "file_path": "/uploads/test.xlsx",
        "dataframe_json": [{"Nombre": "Juan"}],
        "status": "confirmed",
        "language": "es",
    }

    repo = ExtractionRepository(pool)
    result = await repo.get_session_with_context(str(session_id))

    assert result is not None
    assert result["id"] == str(session_id)
    assert result["schema_json"] == schema_data
    assert result["enriched_context"] == "Context about the data extraction."
    assert result["file_path"] == "/uploads/test.xlsx"
    assert result["status"] == "confirmed"
    # dataframe_json should be a JSON string when it comes back as dict/list
    assert json.loads(result["dataframe_json"]) == [{"Nombre": "Juan"}]


@pytest.mark.asyncio
async def test_get_session_with_context_handles_string_schema(mock_pool):
    """Test that get_session_with_context handles schema_json as string."""
    pool, conn = mock_pool
    session_id = uuid4()
    schema_str = '{"columns": [{"index": 1, "name": "Edad", "data_type": "número", "example_value": "25"}]}'

    conn.fetchrow.return_value = {
        "id": session_id,
        "schema_json": schema_str,
        "enriched_context": "Some context",
        "file_path": "/path/to/file.xlsx",
        "dataframe_json": "[]",
        "status": "confirmed",
        "language": "es",
    }

    repo = ExtractionRepository(pool)
    result = await repo.get_session_with_context(str(session_id))

    assert result is not None
    assert result["schema_json"] == json.loads(schema_str)
    assert result["dataframe_json"] == "[]"


@pytest.mark.asyncio
async def test_get_session_with_context_returns_none_when_not_found(mock_pool):
    """Test that get_session_with_context returns None if session not found."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = None

    repo = ExtractionRepository(pool)
    result = await repo.get_session_with_context(str(uuid4()))

    assert result is None


@pytest.mark.asyncio
async def test_get_session_with_context_queries_correct_columns(mock_pool):
    """Test that get_session_with_context queries the expected columns."""
    pool, conn = mock_pool
    session_id = uuid4()

    conn.fetchrow.return_value = {
        "id": session_id,
        "schema_json": {"columns": []},
        "enriched_context": None,
        "file_path": None,
        "dataframe_json": "[]",
        "status": "pending",
        "language": "es",
    }

    repo = ExtractionRepository(pool)
    await repo.get_session_with_context(str(session_id))

    call_args = conn.fetchrow.call_args
    sql = call_args[0][0]
    assert "schema_json" in sql
    assert "enriched_context" in sql
    assert "file_path" in sql
    assert "dataframe_json" in sql
    assert "status" in sql
    assert "FROM template_sessions" in sql
