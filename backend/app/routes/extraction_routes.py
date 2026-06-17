"""API routes for the LLM extraction module."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.requests import Request

from app.models import (
    ExtractionErrorResponse,
    ExtractionRecord,
    ExtractionRequest,
    ExtractionResult,
    RecordValue,
    RecordsResponse,
)
from app.repositories import ExtractionRepository
from app.services import (
    ExcelWriter,
    ExtractionOrchestrator,
    LLMExtractionService,
    LLMInvalidResponseError,
    LLMUnavailableError,
    PromptBuilder,
    ResponseParser,
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
        HTTPException 422: Session not confirmed or empty text (Pydantic)
        HTTPException 500: File write/not found or database errors
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
        excel_writer=ExcelWriter(),
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
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=ExtractionErrorResponse(
                detail=str(e),
                error_code="FILE_NOT_FOUND",
            ).model_dump(),
        )
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=ExtractionErrorResponse(
                detail=f"Error al escribir el archivo Excel: {str(e)}",
                error_code="FILE_WRITE_ERROR",
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

    return RecordsResponse(
        records=extraction_records,
        total_rows=len(extraction_records),
    )
