"""Extraction Orchestrator Service.

Coordinates the full extraction flow: get session → build prompt → call LLM →
parse response → insert row into DataFrame → write .xlsx → persist in DB → return result.
"""

import io
from uuid import UUID

import pandas as pd

from app.models import ColumnSchema, ExtractionResult, RecordValue
from app.repositories import ExtractionRepository
from app.services.excel_writer import ExcelWriter
from app.services.llm_extraction_service import LLMExtractionService
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import ResponseParser


class ExtractionOrchestrator:
    """Orchestrates the complete extraction pipeline."""

    def __init__(
        self,
        prompt_builder: PromptBuilder,
        llm_service: LLMExtractionService,
        response_parser: ResponseParser,
        excel_writer: ExcelWriter,
        repository: ExtractionRepository,
    ) -> None:
        self._prompt_builder = prompt_builder
        self._llm_service = llm_service
        self._response_parser = response_parser
        self._excel_writer = excel_writer
        self._repository = repository

    async def process(
        self,
        session_id: str,
        transcribed_text: str,
    ) -> ExtractionResult:
        """Execute the full extraction flow.

        1. Obtener sesión activa (schema, enriched_context, file_path)
        2. Construir prompt
        3. Llamar a Claude
        4. Parsear respuesta
        5. Insertar fila en DataFrame
        6. Escribir .xlsx en disco
        7. Persistir en DB
        8. Retornar resultado

        Args:
            session_id: UUID of the active template session.
            transcribed_text: The transcribed audio text to extract data from.

        Returns:
            ExtractionResult with extraction_id, record values, and row_number.

        Raises:
            ValueError: If session is not found.
            LLMUnavailableError: If Claude API is unreachable.
            LLMInvalidResponseError: If Claude returns invalid JSON.
            FileNotFoundError: If the Excel file is missing.
        """
        # 1. Get session with context
        session = await self._repository.get_session_with_context(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        schema = ColumnSchema(**session["schema_json"])
        enriched_context = session["enriched_context"] or ""
        file_path = session["file_path"]
        dataframe_json = session["dataframe_json"]

        # 2. Build prompt
        prompt = self._prompt_builder.build(
            enriched_context=enriched_context,
            schema=schema,
            transcribed_text=transcribed_text,
        )

        # 3. Call LLM
        raw_response = await self._llm_service.extract(prompt)

        # 4. Parse response
        record = self._response_parser.parse(raw_response, schema)

        # 5. Insert row into DataFrame
        if dataframe_json:
            df = pd.read_json(io.StringIO(dataframe_json))
        else:
            column_names = [col.name for col in schema.columns]
            df = pd.DataFrame(columns=column_names)

        # Compute row_number: 4 + number of existing data rows
        row_number = 4 + len(df)

        # Append the new record as a row
        new_row = pd.DataFrame([record])
        df = pd.concat([df, new_row], ignore_index=True)

        # Serialize DataFrame back to JSON
        updated_dataframe_json = df.to_json()

        # 6. Update DataFrame in DB
        await self._repository.update_dataframe(session_id, updated_dataframe_json)

        # 7. Write .xlsx to disk
        self._excel_writer.write(df, file_path, schema)

        # 8. Persist extraction record in DB
        extraction_id = await self._repository.save_extraction(
            session_id=session_id,
            record=record,
            row_number=row_number,
            transcribed_text=transcribed_text,
        )

        # Build result
        record_values = [
            RecordValue(column_name=col.name, value=record.get(col.name, ""))
            for col in schema.columns
        ]

        return ExtractionResult(
            extraction_id=UUID(extraction_id),
            record=record_values,
            row_number=row_number,
        )
