"""Unit tests for ExtractionOrchestrator service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.constants import MAX_ROWS_PER_SESSION
from app.models import ColumnSchema, ExtractionResult, RecordValue
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.services.exceptions import LLMInvalidResponseError, LLMUnavailableError


@pytest.fixture
def schema_json():
    """Sample schema JSON with 3 columns."""
    return {
        "columns": [
            {"index": 1, "name": "Nombre", "data_type": "texto", "example_value": "Juan"},
            {"index": 2, "name": "Edad", "data_type": "número entero", "example_value": "30"},
            {"index": 3, "name": "Ciudad", "data_type": "texto", "example_value": "Madrid"},
        ]
    }


@pytest.fixture
def session_data(schema_json):
    """Sample session data returned by the repository."""
    return {
        "id": str(uuid4()),
        "schema_json": schema_json,
        "enriched_context": "Contexto de prueba para extracción.",
        "status": "confirmed",
    }


@pytest.fixture
def orchestrator():
    """Create orchestrator with mocked dependencies."""
    prompt_builder = MagicMock()
    prompt_builder.build.return_value = "prompt de prueba"

    llm_service = AsyncMock()
    llm_service.extract.return_value = '{"Nombre": "Carlos", "Edad": "25", "Ciudad": "Lima"}'

    response_parser = MagicMock()
    response_parser.parse.return_value = {
        "Nombre": "Carlos",
        "Edad": "25",
        "Ciudad": "Lima",
    }

    repository = AsyncMock()
    # No records yet by default → first record lands on the first data row.
    repository.count_records.return_value = 0

    return ExtractionOrchestrator(
        prompt_builder=prompt_builder,
        llm_service=llm_service,
        response_parser=response_parser,
        repository=repository,
    )


@pytest.mark.asyncio
async def test_process_happy_path(orchestrator, session_data):
    """Complete happy path: session found → prompt built → LLM called → parsed → persisted."""
    extraction_id = str(uuid4())
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = extraction_id

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Me llamo Carlos, tengo 25 años y vivo en Lima.",
    )

    # Verify result type and content
    assert isinstance(result, ExtractionResult)
    assert str(result.extraction_id) == extraction_id
    assert result.row_number == 2  # First record lands on row 2 (row 1 is the header)
    assert len(result.record) == 3
    assert result.record[0] == RecordValue(column_name="Nombre", value="Carlos")
    assert result.record[1] == RecordValue(column_name="Edad", value="25")
    assert result.record[2] == RecordValue(column_name="Ciudad", value="Lima")

    # Verify the pipeline dependencies were called
    orchestrator._prompt_builder.build.assert_called_once()
    orchestrator._llm_service.extract.assert_called_once_with("prompt de prueba")
    orchestrator._response_parser.parse.assert_called_once()
    orchestrator._repository.count_records.assert_called_once()
    orchestrator._repository.save_extraction.assert_called_once()
    # First record is far below the cap → session stays open.
    orchestrator._repository.mark_finalized.assert_not_called()


@pytest.mark.asyncio
async def test_process_builds_prompt_in_session_language(orchestrator, session_data):
    """The extraction prompt is built in the session's stored language."""
    session_data["language"] = "en"
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="My name is Carlos, I'm 25 and live in Lima.",
    )

    assert orchestrator._prompt_builder.build.call_args.kwargs["language"] == "en"


@pytest.mark.asyncio
async def test_row_number_first_record_is_2(orchestrator, session_data):
    """First record (no existing rows) should get row_number = 2."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.count_records.return_value = 0
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    assert result.row_number == 2


@pytest.mark.asyncio
async def test_row_number_increments_with_existing_records(orchestrator, session_data):
    """Row number should be 2 + number of existing records."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.count_records.return_value = 2
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    # 2 header offset + 2 existing records = row 4 (third record)
    assert result.row_number == 4


@pytest.mark.asyncio
async def test_row_number_with_one_existing_record(orchestrator, session_data):
    """Row number should be 3 when there is 1 existing record."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.count_records.return_value = 1
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    assert result.row_number == 3


@pytest.mark.asyncio
async def test_row_number_derived_from_count_for_same_session(orchestrator, session_data):
    """count_records is queried for the session being processed."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    count_call = orchestrator._repository.count_records.call_args
    assert count_call[0][0] == session_data["id"]


@pytest.mark.asyncio
async def test_does_not_finalize_below_cap(orchestrator, session_data):
    """A record below the cap must not finalize the session."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.count_records.return_value = MAX_ROWS_PER_SESSION - 2
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    orchestrator._repository.mark_finalized.assert_not_called()


@pytest.mark.asyncio
async def test_auto_finalizes_when_cap_reached(orchestrator, session_data):
    """The record that reaches the cap must finalize the session."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    # One short of the cap → this extraction is the last allowed one.
    orchestrator._repository.count_records.return_value = MAX_ROWS_PER_SESSION - 1
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    orchestrator._repository.mark_finalized.assert_called_once_with(session_data["id"])
    # Cap record lands on row FIRST_DATA_ROW + (MAX - 1).
    assert result.row_number == 2 + (MAX_ROWS_PER_SESSION - 1)


@pytest.mark.asyncio
async def test_session_not_found_raises_value_error(orchestrator):
    """Should raise ValueError when the session is not found."""
    orchestrator._repository.get_session_with_context.return_value = None

    with pytest.raises(ValueError, match="Session .* not found"):
        await orchestrator.process(
            session_id=str(uuid4()),
            transcribed_text="Texto de prueba",
        )


@pytest.mark.asyncio
async def test_llm_unavailable_propagates(orchestrator, session_data):
    """LLMUnavailableError from the LLM service should propagate."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._llm_service.extract.side_effect = LLMUnavailableError(
        "El servicio LLM no está disponible"
    )

    with pytest.raises(LLMUnavailableError):
        await orchestrator.process(
            session_id=session_data["id"],
            transcribed_text="Texto de prueba",
        )

    # No record should be saved when extraction fails.
    orchestrator._repository.save_extraction.assert_not_called()


@pytest.mark.asyncio
async def test_llm_invalid_response_propagates(orchestrator, session_data):
    """LLMInvalidResponseError from the response parser should propagate."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._response_parser.parse.side_effect = LLMInvalidResponseError(
        detail="La respuesta del LLM no es JSON válido"
    )

    with pytest.raises(LLMInvalidResponseError):
        await orchestrator.process(
            session_id=session_data["id"],
            transcribed_text="Texto de prueba",
        )

    orchestrator._repository.save_extraction.assert_not_called()


@pytest.mark.asyncio
async def test_prompt_builder_receives_correct_args(orchestrator, session_data):
    """PromptBuilder should receive enriched_context, schema, and transcribed_text."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Me llamo Carlos",
    )

    call_kwargs = orchestrator._prompt_builder.build.call_args[1]
    assert call_kwargs["enriched_context"] == "Contexto de prueba para extracción."
    assert call_kwargs["transcribed_text"] == "Me llamo Carlos"
    assert isinstance(call_kwargs["schema"], ColumnSchema)


@pytest.mark.asyncio
async def test_save_extraction_receives_correct_args(orchestrator, session_data):
    """save_extraction should receive session_id, record dict, row_number, and text."""
    extraction_id = str(uuid4())
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = extraction_id

    await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto original",
    )

    call_kwargs = orchestrator._repository.save_extraction.call_args[1]
    assert call_kwargs["session_id"] == session_data["id"]
    assert call_kwargs["record"] == {"Nombre": "Carlos", "Edad": "25", "Ciudad": "Lima"}
    assert call_kwargs["row_number"] == 2
    assert call_kwargs["transcribed_text"] == "Texto original"
