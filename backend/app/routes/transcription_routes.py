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
from app.rate_limit import (
    BILLABLE_RATE_LIMIT_DAY,
    BILLABLE_RATE_LIMIT_HOUR,
    limiter,
)
from app.repositories import (
    TemplateRepository,
    TranscriptionRepository,
    UsageRepository,
)
from app.services import (
    OPERATION_TRANSCRIPTION,
    AcceptanceValidator,
    AudioDurationProbe,
    AudioUnreadableError,
    AudioValidator,
    UsageBudget,
    WhisperEmptyResponseError,
    WhisperNoSpeechError,
    WhisperTranscriptionService,
    WhisperUnavailableError,
)

router = APIRouter(prefix="/api/transcriptions", tags=["transcriptions"])

# Container hint for the duration probe. ffprobe detects the format from content,
# so this only helps the occasional ambiguous stream — it is never trusted.
_SUFFIX_BY_MIME = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
}


def _suffix_for(file: UploadFile) -> str:
    base_type = (file.content_type or "").split(";")[0].strip().lower()
    return _SUFFIX_BY_MIME.get(base_type, "")


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
@limiter.limit(BILLABLE_RATE_LIMIT_HOUR)
@limiter.limit(BILLABLE_RATE_LIMIT_DAY)
async def transcribe_audio(
    request: Request,
    file: UploadFile,
    duration: float | None = Form(default=None),
):
    """Transcribe an uploaded audio file using OpenAI Whisper API.

    Flow:
    1. Cheap upload checks (non-empty, byte ceiling, MIME type)
    2. **Measure** the audio's real duration and validate it (ADR-0019)
    3. Verify an active (confirmed) template session exists
    4. Send audio to Whisper API for transcription
    5. Persist transcription session in database
    6. Return transcription_id and transcribed text

    Args:
        duration: The duration the CLIENT reports. Accepted for backward
            compatibility and telemetry only — it is **never** used as a control.
            Until ADR-0019 this field *was* the enforcement, which made the cap
            fictional: a request could claim 5 s while carrying ten minutes of
            audio and Whisper billed the ten. The number that matters now comes
            from measuring the file.
    """
    # 1. Cheap checks first: never pay to decode an upload already known to be
    #    invalid (the probe writes a temp file and spawns a process).
    validator = AudioValidator()
    upload_result = validator.validate_upload(file)

    if not upload_result.is_valid:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                detail=upload_result.detail or "Validation failed",
                error_code=upload_result.error_code or "VALIDATION_ERROR",
            ).model_dump(),
        )

    # 2. Measure the REAL duration from the bytes, then validate that measurement.
    #    This is the trust boundary: everything the client said about this file is
    #    now irrelevant.
    file.file.seek(0)
    audio_bytes = await file.read()

    probe = AudioDurationProbe()
    try:
        measured_duration = await probe.measure_seconds(
            audio_bytes, suffix=_suffix_for(file)
        )
    except AudioUnreadableError as e:
        # Fail closed: an unmeasurable file is indistinguishable from one hiding an
        # hour of audio, and we have not spent anything on it yet.
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(detail=e.detail, error_code=e.error_code).model_dump(),
        )

    validation_result = validator.validate(file, measured_duration)

    if not validation_result.is_valid:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                detail=validation_result.detail or "Validation failed",
                error_code=validation_result.error_code or "VALIDATION_ERROR",
            ).model_dump(),
        )

    # 3. Verify active template session exists
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

    # 4. Global spend ceiling (ADR-0019 §3). Checked HERE — immediately before the
    #    only billable call in this handler — so a request rejected for any other
    #    reason never pays a database round trip, and a blocked request never
    #    reaches OpenAI.
    budget = UsageBudget(UsageRepository(pool))
    await budget.check()

    # 5. Send audio to Whisper API (bytes already read for the probe in step 2)
    mime_type = file.content_type or "audio/webm"

    # The spoken language is the one fixed when the template was confirmed
    # (per-session, ADR-0012), not a per-request value.
    spoken_language = active_session.language

    whisper_service = WhisperTranscriptionService()
    try:
        text = await whisper_service.transcribe(audio_bytes, mime_type, spoken_language)
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

    # 6. Charge the ledger. AFTER the call, never before: a failed Whisper call
    #    costs nothing and must not consume budget.
    await budget.record(OPERATION_TRANSCRIPTION, session_id=active_session.id)

    # 6b. Funnel: the "aha" moment (ADR-0019 §7). Idempotent in SQL, so the second
    #     narration onward changes nothing. Best-effort — a telemetry write must
    #     never cost the user a transcription they already paid for.
    try:
        await template_repo.mark_first_narration(str(active_session.id))
    except Exception:
        pass

    # 7. Persist transcription session. We store the MEASURED duration, not the
    #    client's claim — it is the value the cost was actually incurred on, so it
    #    is also the one worth keeping for the usage ledger.
    transcription_repo = TranscriptionRepository(pool)
    transcription_id = await transcription_repo.create_session(
        template_session_id=active_session.id,
        text=text,
        duration_seconds=measured_duration,
    )

    # 8. Return response
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
