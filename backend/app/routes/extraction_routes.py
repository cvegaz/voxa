"""API routes for the LLM extraction module."""

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from fastapi.responses import StreamingResponse

from app.constants import MAX_ROWS_PER_SESSION
from app.models import (
    ColumnSchema,
    ExtractionErrorResponse,
    ExtractionRecord,
    ExtractionRequest,
    ExtractionResult,
    FinalizeResponse,
    RecordValue,
    RecordsResponse,
)
from app.repositories import ExtractionRepository
from app.services import (
    ExcelExporter,
    ExtractionOrchestrator,
    LLMExtractionService,
    LLMInvalidResponseError,
    LLMUnavailableError,
    PromptBuilder,
    ResponseParser,
)

# OOXML (.xlsx) MIME type for the download response.
XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

router = APIRouter(prefix="/api/extraction", tags=["extraction"])


@router.post(
    "/process",
    response_model=ExtractionResult,
    responses={
        404: {"model": ExtractionErrorResponse},
        422: {"model": ExtractionErrorResponse},
        500: {"model": ExtractionErrorResponse},
        502: {"model": ExtractionErrorResponse},
    },
)
async def process_extraction(request: Request, body: ExtractionRequest):
    """Process a transcribed text through LLM extraction.

    Flow:
    1. Validate session exists and is confirmed
    2. Call ExtractionOrchestrator.process() to extract fields via LLM
    3. Return ExtractionResult with extraction_id, record, and row_number

    Raises:
        HTTPException 404: Session not found
        HTTPException 422: Session not confirmed, finalized, or empty text
        HTTPException 500: Database or unexpected errors
        HTTPException 502: LLM unavailable or invalid response
    """
    pool = request.app.state.pool
    repo = ExtractionRepository(pool)

    # Validate session exists
    session = await repo.get_session_with_context(str(body.session_id))

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=ExtractionErrorResponse(
                detail=f"Sesión {body.session_id} no encontrada.",
                error_code="SESSION_NOT_FOUND",
            ).model_dump(),
        )

    # A finalized session is closed and accepts no more records (ADR-0013).
    if session["status"] == "finalized":
        raise HTTPException(
            status_code=422,
            detail=ExtractionErrorResponse(
                detail="La sesión ya fue finalizada y no admite más registros.",
                error_code="SESSION_FINALIZED",
            ).model_dump(),
        )

    # Validate session is confirmed
    if session["status"] != "confirmed":
        raise HTTPException(
            status_code=422,
            detail=ExtractionErrorResponse(
                detail=f"La sesión {body.session_id} no está confirmada.",
                error_code="SESSION_NOT_CONFIRMED",
            ).model_dump(),
        )

    # Build orchestrator with all dependencies
    orchestrator = ExtractionOrchestrator(
        prompt_builder=PromptBuilder(),
        llm_service=LLMExtractionService(),
        response_parser=ResponseParser(),
        repository=repo,
    )

    try:
        result = await orchestrator.process(
            session_id=str(body.session_id),
            transcribed_text=body.transcribed_text,
        )
    except LLMUnavailableError as e:
        raise HTTPException(
            status_code=502,
            detail=ExtractionErrorResponse(
                detail=e.detail,
                error_code=e.error_code,
            ).model_dump(),
        )
    except LLMInvalidResponseError as e:
        raise HTTPException(
            status_code=502,
            detail=ExtractionErrorResponse(
                detail=e.detail,
                error_code=e.error_code,
            ).model_dump(),
        )
    except Exception as e:
        # Database errors or unexpected failures
        raise HTTPException(
            status_code=500,
            detail=ExtractionErrorResponse(
                detail=f"Error interno del servidor: {str(e)}",
                error_code="DATABASE_ERROR",
            ).model_dump(),
        )

    return result


@router.get(
    "/records/{session_id}",
    response_model=RecordsResponse,
    responses={404: {"model": ExtractionErrorResponse}},
)
async def get_extraction_records(request: Request, session_id: UUID):
    """Retrieve all extraction records for a session.

    Returns only data rows (not headers), ordered by row_number ASC.
    Each record's record_json dict is mapped to a list of RecordValue objects.
    """
    pool = request.app.state.pool
    repo = ExtractionRepository(pool)

    records = await repo.get_records(str(session_id))

    extraction_records = []
    for rec in records:
        # Map record_json dict to list of RecordValue
        record_values = [
            RecordValue(column_name=key, value=value)
            for key, value in rec["record_json"].items()
        ]

        extraction_records.append(
            ExtractionRecord(
                extraction_id=UUID(rec["id"]),
                row_number=rec["row_number"],
                record=record_values,
                transcribed_text=rec["transcribed_text"],
                created_at=rec["created_at"],
            )
        )

    finalized = await repo.get_status(str(session_id)) == "finalized"

    return RecordsResponse(
        records=extraction_records,
        total_rows=len(extraction_records),
        max_rows=MAX_ROWS_PER_SESSION,
        finalized=finalized,
    )


@router.post(
    "/finalize/{session_id}",
    response_model=FinalizeResponse,
    responses={
        404: {"model": ExtractionErrorResponse},
        422: {"model": ExtractionErrorResponse},
    },
)
async def finalize_session(request: Request, session_id: UUID):
    """Close a capture session so its Excel can be downloaded (ADR-0013).

    Idempotent: finalizing an already-finalized session is a no-op that returns
    the current state. Only confirmed (or already-finalized) sessions can be
    finalized.

    Raises:
        HTTPException 404: Session not found
        HTTPException 422: Session not in a confirmable state (pending/replaced)
    """
    pool = request.app.state.pool
    repo = ExtractionRepository(pool)

    status = await repo.get_status(str(session_id))

    if status is None:
        raise HTTPException(
            status_code=404,
            detail=ExtractionErrorResponse(
                detail=f"Sesión {session_id} no encontrada.",
                error_code="SESSION_NOT_FOUND",
            ).model_dump(),
        )

    if status not in ("confirmed", "finalized"):
        raise HTTPException(
            status_code=422,
            detail=ExtractionErrorResponse(
                detail=f"La sesión {session_id} no está confirmada.",
                error_code="SESSION_NOT_CONFIRMED",
            ).model_dump(),
        )

    if status != "finalized":
        await repo.mark_finalized(str(session_id))

    total_rows = await repo.count_records(str(session_id))

    return FinalizeResponse(status="finalized", total_rows=total_rows)


@router.get(
    "/export/{session_id}",
    responses={
        200: {"content": {XLSX_MEDIA_TYPE: {}}},
        404: {"model": ExtractionErrorResponse},
    },
)
async def export_excel(request: Request, session_id: UUID):
    """Download the session's data as a freshly built ``.xlsx`` (ADR-0013).

    The file is reconstructed in memory from the schema + records: a single
    header row of column names followed by the captured rows. The template's
    Tipo_Dato/Ejemplo_Valor scaffolding is never included. Available at any time
    (finalized or not), so a partial capture can also be downloaded.

    Raises:
        HTTPException 404: Session not found
    """
    pool = request.app.state.pool
    repo = ExtractionRepository(pool)

    context = await repo.get_export_context(str(session_id))
    if context is None:
        raise HTTPException(
            status_code=404,
            detail=ExtractionErrorResponse(
                detail=f"Sesión {session_id} no encontrada.",
                error_code="SESSION_NOT_FOUND",
            ).model_dump(),
        )

    schema = ColumnSchema(**context["schema_json"])
    records = await repo.get_records(str(session_id))
    row_dicts = [rec["record_json"] for rec in records]

    content = ExcelExporter().build(schema, row_dicts)

    file_name = context["file_name"] or "export.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{file_name}"'}
    return StreamingResponse(
        BytesIO(content),
        media_type=XLSX_MEDIA_TYPE,
        headers=headers,
    )
