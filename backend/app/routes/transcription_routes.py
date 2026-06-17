"""API routes for the audio transcription controls module."""

from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.requests import Request

from app.models import (
    AcceptRequest,
    AcceptResponse,
    TranscriptionErrorResponse,
)
from app.models.transcription_models import (
    ErrorResponse,
    ResetRequest,
    ResetResponse,
    TranscribeResponse,
    TranscriptionSession,
)
from app.repositories import TemplateRepository, TranscriptionRepository
from app.services import (
    AcceptanceValidator,
    AudioValidator,
    WhisperEmptyResponseError,
    WhisperNoSpeechError,
    WhisperTranscriptionService,
    WhisperUnavailableError,
)

router = APIRouter(prefix="/api/transcriptions", tags=["transcriptions"])


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def transcribe_audio(
    request: Request,
    file: UploadFile,
    duration: float = Form(...),
):
    """Transcribe an uploaded audio file using OpenAI Whisper API.

    Flow:
    1. Validate audio file (MIME type, duration, non-empty)
    2. Verify an active (confirmed) template session exists
    3. Send audio to Whisper API for transcription
    4. Persist transcription session in database
    5. Return transcription_id and transcribed text
    """
    # 1. Validate audio file
    validator = AudioValidator()
    validation_result = validator.validate(file, duration)

    if not validation_result.is_valid:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                detail=validation_result.detail or "Validation failed",
                error_code=validation_result.error_code or "VALIDATION_ERROR",
            ).model_dump(),
        )

    # 2. Verify active template session exists
    pool = request.app.state.pool
    template_repo = TemplateRepository(pool)
    active_session = await template_repo.get_active_session()

    if active_session is None:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                detail="No se encontró un esquema de columnas confirmado. Suba y confirme una plantilla primero.",
                error_code="NO_CONFIRMED_SCHEMA",
            ).model_dump(),
        )

    # 3. Send audio to Whisper API
    file.file.seek(0)
    audio_bytes = await file.read()
    mime_type = file.content_type or "audio/webm"

    whisper_service = WhisperTranscriptionService()
    try:
        text = await whisper_service.transcribe(audio_bytes, mime_type)
    except WhisperNoSpeechError as e:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                detail=e.detail,
                error_code=e.error_code,
            ).model_dump(),
        )
    except WhisperUnavailableError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                detail=e.detail,
                error_code=e.error_code,
            ).model_dump(),
        )
    except WhisperEmptyResponseError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                detail=e.detail,
                error_code=e.error_code,
            ).model_dump(),
        )

    # 4. Persist transcription session
    transcription_repo = TranscriptionRepository(pool)
    transcription_id = await transcription_repo.create_session(
        template_session_id=active_session.id,
        text=text,
        duration_seconds=duration,
    )

    # 5. Return response
    return TranscribeResponse(
        transcription_id=transcription_id,
        text=text,
    )


@router.post(
    "/accept",
    response_model=AcceptResponse,
    responses={
        404: {"model": TranscriptionErrorResponse},
        409: {"model": TranscriptionErrorResponse},
        422: {"model": TranscriptionErrorResponse},
    },
)
async def accept_transcription(request: Request, body: AcceptRequest):
    """Accept a transcription session with the final text.

    Validates preconditions (session exists, text non-empty, schema confirmed),
    then marks the session as accepted and persists the final text.

    Args:
        body: AcceptRequest with transcription_id and text.

    Returns:
        AcceptResponse with status "accepted".

    Raises:
        HTTPException 404: Session not found or not in pending status.
        HTTPException 409: No confirmed schema exists.
        HTTPException 422: Text is empty or whitespace-only.
    """
    pool = request.app.state.pool
    transcription_repo = TranscriptionRepository(pool)
    template_repo = TemplateRepository(pool)

    # Validate preconditions
    validator = AcceptanceValidator(transcription_repo, template_repo)
    result = await validator.validate(body.transcription_id, body.text)

    if not result.is_valid:
        # Map error codes to HTTP status codes
        error_code = result.error_code or "VALIDATION_ERROR"
        status_code_map = {
            "SESSION_NOT_FOUND": 404,
            "EMPTY_TRANSCRIPTION": 422,
            "NO_CONFIRMED_SCHEMA": 409,
        }
        status_code = status_code_map.get(error_code, 422)

        raise HTTPException(
            status_code=status_code,
            detail=TranscriptionErrorResponse(
                detail=result.detail or "Validation failed",
                error_code=error_code,
            ).model_dump(),
        )

    # Accept the session
    await transcription_repo.accept_session(body.transcription_id, body.text)

    return AcceptResponse(status="accepted")


@router.post(
    "/reset",
    response_model=ResetResponse,
    responses={404: {"model": ErrorResponse}},
)
async def reset_transcription(request: Request, body: ResetRequest):
    """Reset (discard) a transcription session.

    Marks the transcription session as 'discarded', clearing the transcription
    state while preserving the associated template schema (Esquema_Columnas).

    Args:
        body: ResetRequest containing the transcription_id to discard.

    Returns:
        ResetResponse with status "reset" on success.

    Raises:
        HTTPException 404: If the session is not found or not in 'pending' status.
    """
    pool = request.app.state.pool
    repo = TranscriptionRepository(pool)

    try:
        await repo.discard_session(body.transcription_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                detail=f"Transcription session {body.transcription_id} not found or not in 'pending' status.",
                error_code="SESSION_NOT_FOUND",
            ).model_dump(),
        )

    return ResetResponse(status="reset")


@router.get(
    "/{id}",
    response_model=TranscriptionSession,
    responses={404: {"model": ErrorResponse}},
)
async def get_transcription(request: Request, id: UUID):
    """Retrieve a transcription session by its ID.

    Returns the full TranscriptionSession data.
    Returns 404 if the session is not found.
    """
    pool = request.app.state.pool
    repo = TranscriptionRepository(pool)

    session = await repo.get_session(id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                detail=f"Transcription session {id} not found.",
                error_code="SESSION_NOT_FOUND",
            ).model_dump(),
        )

    return session
