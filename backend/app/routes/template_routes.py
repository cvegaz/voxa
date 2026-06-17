"""API routes for the Excel template loader module."""

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.requests import Request
from fastapi.responses import Response
from openpyxl import load_workbook

from app.models import ActiveSessionResponse, ConfirmRequest, ConfirmResponse, ErrorResponse, UploadResponse
from app.repositories import TemplateRepository
from app.services import (
    ContextValidator,
    DataFrameConverter,
    ExcelValidator,
    LLMEnrichmentService,
    LLMInvalidResponseError,
    LLMUnavailableError,
    SchemaExtractor,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={422: {"model": ErrorResponse}},
)
async def upload_template(request: Request, file: UploadFile):
    """Upload and process an Excel template file.

    Flow:
    1. Validate file structure (extension, columns, rows 1-3)
    2. Extract column schema from rows 1-3
    3. Convert workbook content to DataFrame
    4. Replace any existing pending/confirmed sessions
    5. Create a new session in the database
    6. Return session_id, schema, and file_name
    """
    # 1. Validate
    validator = ExcelValidator()
    validation_result = validator.validate(file)

    if not validation_result.is_valid:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                detail=validation_result.detail or "Validation failed",
                error_code=validation_result.error_code or "VALIDATION_ERROR",
            ).model_dump(),
        )

    # 2. Load workbook once for schema extraction and DataFrame conversion
    file.file.seek(0)
    content = file.file.read()
    workbook = load_workbook(BytesIO(content), data_only=True)

    try:
        # 3. Extract schema
        extractor = SchemaExtractor()
        schema = extractor.extract(workbook)

        # 4. Convert to DataFrame
        converter = DataFrameConverter()
        df = converter.convert(workbook, schema)
    finally:
        workbook.close()

    # Serialize DataFrame as JSON for storage
    dataframe_json = df.to_json(orient="records", force_ascii=False)

    # 5. Get repository from app state (database pool)
    pool = request.app.state.pool
    repo = TemplateRepository(pool)

    # 6. Replace previous sessions
    await repo.replace_previous_sessions()

    # 7. Create new session
    session_id = await repo.create_session(
        schema=schema,
        dataframe_json=dataframe_json,
        file_name=file.filename or "unknown.xlsx",
    )

    # 8. Return response
    return UploadResponse(
        session_id=UUID(session_id),
        column_schema=schema,
        file_name=file.filename or "unknown.xlsx",
    )


@router.post(
    "/confirm",
    response_model=ConfirmResponse,
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def confirm_template(request: Request, body: ConfirmRequest):
    """Confirm a template session with user-provided context.

    Flow:
    1. Retrieve session by ID and verify it exists with status 'pending'
    2. Validate context text (length constraints)
    3. Call LLM enrichment service with context + schema
    4. Persist enriched context and mark session as confirmed
    5. Return enriched context
    """
    pool = request.app.state.pool
    repo = TemplateRepository(pool)

    # 1. Retrieve session and verify it's pending
    session = await repo.get_session_by_id(str(body.session_id))

    if session is None or session.status != "pending":
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                detail=f"Session {body.session_id} not found or not in 'pending' state.",
                error_code="SESSION_NOT_FOUND",
            ).model_dump(),
        )

    # 2. Validate context
    context_validator = ContextValidator()
    validation_result = context_validator.validate(body.context)

    if not validation_result.is_valid:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                detail=validation_result.detail or "Context validation failed",
                error_code=validation_result.error_code or "VALIDATION_ERROR",
            ).model_dump(),
        )

    # 3. Call LLM enrichment
    llm_service = LLMEnrichmentService()
    try:
        enriched_context = await llm_service.enrich(
            context=body.context,
            schema=session.column_schema,
        )
    except LLMUnavailableError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                detail=e.detail,
                error_code=e.error_code,
            ).model_dump(),
        )
    except LLMInvalidResponseError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                detail=e.detail,
                error_code=e.error_code,
            ).model_dump(),
        )

    # 4. Persist enriched context and mark session as confirmed
    await repo.confirm_session(
        session_id=str(body.session_id),
        enriched_context=enriched_context,
        user_context=body.context,
    )

    # 5. Return enriched context
    return ConfirmResponse(enriched_context=enriched_context)


@router.get(
    "/active",
    response_model=ActiveSessionResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_active_session(request: Request):
    """Retrieve the current active (confirmed) template session.

    Returns the most recently confirmed session with its schema,
    enriched context, and confirmation timestamp.
    Returns 404 if no active session exists.
    """
    pool = request.app.state.pool
    repo = TemplateRepository(pool)

    session = await repo.get_active_session()

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                detail="No active template session found.",
                error_code="SESSION_NOT_FOUND",
            ).model_dump(),
        )

    return ActiveSessionResponse(
        session_id=session.id,
        column_schema=session.column_schema,
        enriched_context=session.enriched_context,
        file_name=session.file_name,
        confirmed_at=session.confirmed_at,
    )


@router.delete(
    "/{session_id}",
    status_code=204,
    responses={404: {"model": ErrorResponse}},
)
async def delete_template(request: Request, session_id: UUID):
    """Delete (mark as replaced) a template session.

    Args:
        session_id: The UUID of the session to delete.

    Returns:
        204 No Content on success.
        404 if session not found or already replaced.
    """
    pool = request.app.state.pool
    repo = TemplateRepository(pool)

    found = await repo.mark_session_replaced(str(session_id))

    if not found:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                detail=f"Session {session_id} not found.",
                error_code="SESSION_NOT_FOUND",
            ).model_dump(),
        )

    return Response(status_code=204)
