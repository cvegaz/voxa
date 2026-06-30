"""Extraction Orchestrator Service.

Coordinates the extraction flow: get session → build prompt → call LLM →
parse response → persist the record → return result.

Per ADR-0013, nothing is written to disk and no parallel DataFrame is kept:
``extraction_records`` is the single source of truth, and the final ``.xlsx`` is
reconstructed from the schema on demand at export time.
"""

from uuid import UUID

from app.constants import FIRST_DATA_ROW, MAX_ROWS_PER_SESSION
from app.models import ColumnSchema, ExtractionResult, RecordValue
from app.repositories import ExtractionRepository
from app.services.llm_extraction_service import LLMExtractionService
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import ResponseParser


class ExtractionOrchestrator:
    """Orchestrates the extraction pipeline."""

    def __init__(
        self,
        prompt_builder: PromptBuilder,
        llm_service: LLMExtractionService,
        response_parser: ResponseParser,
        repository: ExtractionRepository,
    ) -> None:
        self._prompt_builder = prompt_builder
        self._llm_service = llm_service
        self._response_parser = response_parser
        self._repository = repository

    async def process(
        self,
        session_id: str,
        transcribed_text: str,
    ) -> ExtractionResult:
        """Execute the full extraction flow.

        1. Get the active session (schema, enriched_context)
        2. Build the prompt
        3. Call the LLM
        4. Parse the response
        5. Derive row_number from the record count, persist the record
        6. Return the result

        Args:
            session_id: UUID of the active template session.
            transcribed_text: The transcribed audio text to extract data from.

        Returns:
            ExtractionResult with extraction_id, record values, and row_number.

        Raises:
            ValueError: If session is not found.
            LLMUnavailableError: If the LLM API is unreachable.
            LLMInvalidResponseError: If the LLM returns invalid JSON.
        """
        # 1. Get session with context
        session = await self._repository.get_session_with_context(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        schema = ColumnSchema(**session["schema_json"])
        enriched_context = session["enriched_context"] or ""
        language = session.get("language") or "es"

        # 2. Build prompt in the session's language
        prompt = self._prompt_builder.build(
            enriched_context=enriched_context,
            schema=schema,
            transcribed_text=transcribed_text,
            language=language,
        )

        # 3. Call LLM
        raw_response = await self._llm_service.extract(prompt)

        # 4. Parse response
        record = self._response_parser.parse(raw_response, schema)

        # 5. Derive row_number from the authoritative record count and persist.
        #    extraction_records is the single source of truth (ADR-0013), so the
        #    Nth record lands on row FIRST_DATA_ROW + (N-1): each recording adds
        #    exactly one row and the next goes to the next number, with no
        #    parallel counter to drift out of sync.
        existing_count = await self._repository.count_records(session_id)
        row_number = FIRST_DATA_ROW + existing_count

        extraction_id = await self._repository.save_extraction(
            session_id=session_id,
            record=record,
            row_number=row_number,
            transcribed_text=transcribed_text,
        )

        # 5b. Auto-finalize when the row cap is reached (ADR-0013). The session
        #     then accepts no further extractions; the refetched records carry
        #     the finalized flag so the UI can enable the download.
        if existing_count + 1 >= MAX_ROWS_PER_SESSION:
            await self._repository.mark_finalized(session_id)

        # 6. Build result
        record_values = [
            RecordValue(column_name=col.name, value=record.get(col.name, ""))
            for col in schema.columns
        ]

        return ExtractionResult(
            extraction_id=UUID(extraction_id),
            record=record_values,
            row_number=row_number,
        )
