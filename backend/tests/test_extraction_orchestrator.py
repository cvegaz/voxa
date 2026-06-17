"""Unit tests for ExtractionOrchestrator service."""

import io
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

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
    """Sample session data returned by repository."""
    empty_df = pd.DataFrame(columns=["Nombre", "Edad", "Ciudad"])
    return {
        "id": str(uuid4()),
        "schema_json": schema_json,
        "enriched_context": "Contexto de prueba para extracción.",
        "file_path": "/tmp/test_file.xlsx",
        "dataframe_json": empty_df.to_json(),
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

    excel_writer = MagicMock()
    excel_writer.write.return_value = None

    repository = AsyncMock()

    return ExtractionOrchestrator(
        prompt_builder=prompt_builder,
        llm_service=llm_service,
        response_parser=response_parser,
        excel_writer=excel_writer,
        repository=repository,
    )


@pytest.mark.asyncio
async def test_process_happy_path(orchestrator, session_data):
    """Test complete happy path: session found → prompt built → LLM called → parsed → written → persisted."""
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
    assert result.row_number == 4  # First record starts at row 4
    assert len(result.record) == 3
    assert result.record[0] == RecordValue(column_name="Nombre", value="Carlos")
    assert result.record[1] == RecordValue(column_name="Edad", value="25")
    assert result.record[2] == RecordValue(column_name="Ciudad", value="Lima")

    # Verify all dependencies were called
    orchestrator._prompt_builder.build.assert_called_once()
    orchestrator._llm_service.extract.assert_called_once_with("prompt de prueba")
    orchestrator._response_parser.parse.assert_called_once()
    orchestrator._excel_writer.write.assert_called_once()
    orchestrator._repository.update_dataframe.assert_called_once()
    orchestrator._repository.save_extraction.assert_called_once()


@pytest.mark.asyncio
async def test_row_number_first_record_is_4(orchestrator, session_data):
    """First record inserted should have row_number = 4."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    assert result.row_number == 4


@pytest.mark.asyncio
async def test_row_number_increments_for_existing_rows(orchestrator, schema_json):
    """Row number should be 4 + number of existing rows in DataFrame."""
    # Create a DataFrame with 2 existing rows
    existing_df = pd.DataFrame([
        {"Nombre": "Ana", "Edad": "28", "Ciudad": "Bogotá"},
        {"Nombre": "Luis", "Edad": "35", "Ciudad": "Quito"},
    ])

    session_data = {
        "id": str(uuid4()),
        "schema_json": schema_json,
        "enriched_context": "Contexto",
        "file_path": "/tmp/test.xlsx",
        "dataframe_json": existing_df.to_json(),
        "status": "confirmed",
    }

    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    # 4 + 2 existing rows = 6
    assert result.row_number == 6


@pytest.mark.asyncio
async def test_row_number_with_one_existing_row(orchestrator, schema_json):
    """Row number should be 5 when there's 1 existing row."""
    existing_df = pd.DataFrame([
        {"Nombre": "Ana", "Edad": "28", "Ciudad": "Bogotá"},
    ])

    session_data = {
        "id": str(uuid4()),
        "schema_json": schema_json,
        "enriched_context": "Contexto",
        "file_path": "/tmp/test.xlsx",
        "dataframe_json": existing_df.to_json(),
        "status": "confirmed",
    }

    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    assert result.row_number == 5


@pytest.mark.asyncio
async def test_session_not_found_raises_value_error(orchestrator):
    """Should raise ValueError when session is not found."""
    orchestrator._repository.get_session_with_context.return_value = None

    with pytest.raises(ValueError, match="Session .* not found"):
        await orchestrator.process(
            session_id=str(uuid4()),
            transcribed_text="Texto de prueba",
        )


@pytest.mark.asyncio
async def test_llm_unavailable_propagates(orchestrator, session_data):
    """LLMUnavailableError from LLM service should propagate."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._llm_service.extract.side_effect = LLMUnavailableError(
        "El servicio LLM no está disponible"
    )

    with pytest.raises(LLMUnavailableError):
        await orchestrator.process(
            session_id=session_data["id"],
            transcribed_text="Texto de prueba",
        )


@pytest.mark.asyncio
async def test_llm_invalid_response_propagates(orchestrator, session_data):
    """LLMInvalidResponseError from response parser should propagate."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._response_parser.parse.side_effect = LLMInvalidResponseError(
        detail="La respuesta del LLM no es JSON válido"
    )

    with pytest.raises(LLMInvalidResponseError):
        await orchestrator.process(
            session_id=session_data["id"],
            transcribed_text="Texto de prueba",
        )


@pytest.mark.asyncio
async def test_file_not_found_propagates(orchestrator, session_data):
    """FileNotFoundError from ExcelWriter should propagate."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())
    orchestrator._excel_writer.write.side_effect = FileNotFoundError(
        "El archivo Excel no fue encontrado"
    )

    with pytest.raises(FileNotFoundError):
        await orchestrator.process(
            session_id=session_data["id"],
            transcribed_text="Texto de prueba",
        )


@pytest.mark.asyncio
async def test_dataframe_updated_before_excel_write(orchestrator, session_data):
    """Verify update_dataframe is called with the updated DataFrame JSON."""
    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    # Verify update_dataframe was called
    call_args = orchestrator._repository.update_dataframe.call_args
    updated_json = call_args[1]["dataframe_json"] if call_args[1] else call_args[0][1]

    # The updated DataFrame should have 1 row (the inserted record)
    updated_df = pd.read_json(io.StringIO(updated_json))
    assert len(updated_df) == 1
    assert updated_df.iloc[0]["Nombre"] == "Carlos"
    assert str(updated_df.iloc[0]["Edad"]) == "25"
    assert updated_df.iloc[0]["Ciudad"] == "Lima"


@pytest.mark.asyncio
async def test_empty_dataframe_json_creates_new_df(orchestrator, schema_json):
    """When dataframe_json is empty/None, a new empty DataFrame should be created."""
    session_data = {
        "id": str(uuid4()),
        "schema_json": schema_json,
        "enriched_context": "Contexto",
        "file_path": "/tmp/test.xlsx",
        "dataframe_json": None,
        "status": "confirmed",
    }

    orchestrator._repository.get_session_with_context.return_value = session_data
    orchestrator._repository.save_extraction.return_value = str(uuid4())

    result = await orchestrator.process(
        session_id=session_data["id"],
        transcribed_text="Texto de prueba",
    )

    # First record on empty DF → row 4
    assert result.row_number == 4


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
    assert call_kwargs["row_number"] == 4
    assert call_kwargs["transcribed_text"] == "Texto original"
