"""API route for the public landing-page contact form."""

from fastapi import APIRouter, HTTPException
from fastapi.requests import Request

from app.models.contact_models import ContactRequest, ContactResponse
from app.models.transcription_models import ErrorResponse
from app.rate_limit import CONTACT_RATE_LIMIT, limiter
from app.repositories import ContactRepository
from app.services import ContactService

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post(
    "",
    response_model=ContactResponse,
    responses={
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
@limiter.limit(CONTACT_RATE_LIMIT)
async def submit_contact(request: Request, body: ContactRequest):
    """Receive a contact-form submission from the landing page.

    Flow:
    1. (slowapi) rate-limit per IP to blunt automated floods.
    2. Drop spam silently via the honeypot field (still returns 200).
    3. Persist the message and, if SMTP is configured, notify the owner.

    Returns 200 with ``status: "received"`` for both real and honeypot
    submissions, so bots cannot distinguish a rejected attempt.
    """
    pool = request.app.state.pool
    repository = ContactRepository(pool)
    service = ContactService(repository)

    try:
        message_id = await service.submit(body)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                detail="No se pudo registrar el mensaje. Inténtalo de nuevo más tarde.",
                error_code="CONTACT_PERSIST_FAILED",
            ).model_dump(),
        )

    return ContactResponse(id=message_id, status="received")
