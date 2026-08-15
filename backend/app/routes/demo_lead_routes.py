"""API route for demo lead capture (ADR-0019 §5).

The soft gate. An address is asked for at the two moments of demonstrated
interest — finishing a capture, and hitting the trial wall — and **nothing about
the demo changes based on the answer**. The download proceeds, the quota is
untouched, no session is created.

That last part is the design, not an omission. An unverified email that buys quota
is a Sybil hole (fabricate identities to evade a per-identity limit): type a new
address, get more. Verification is what would make an address scarce, and it needs
a sending domain Voxa does not have yet. Until then the honest posture is to
collect the address and grant nothing for it.
"""

import os

from fastapi import APIRouter, HTTPException
from fastapi.requests import Request

from app.models import DemoLeadRequest, DemoLeadResponse
from app.models.transcription_models import ErrorResponse
from app.rate_limit import limiter
from app.repositories import DemoLeadRepository

router = APIRouter(prefix="/api/demo-leads", tags=["demo-leads"])

# Generous: a human submits this once or twice. The cap only exists to blunt an
# automated flood filling the table with junk.
DEMO_LEAD_RATE_LIMIT = os.getenv("DEMO_LEAD_RATE_LIMIT", "20/hour")


@router.post(
    "",
    response_model=DemoLeadResponse,
    responses={
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
@limiter.limit(DEMO_LEAD_RATE_LIMIT)
async def submit_demo_lead(request: Request, body: DemoLeadRequest):
    """Record an email volunteered from inside the demo.

    Returns ``status: "received"`` for both genuine and honeypot submissions, so
    a bot cannot tell its entry was dropped.
    """
    # Honeypot: a hidden field only bots fill in. Dropped silently.
    if body.website and body.website.strip():
        return DemoLeadResponse(status="received")

    repository = DemoLeadRepository(request.app.state.pool)

    try:
        await repository.create_lead(
            email=body.email,
            capture_point=body.capture_point,
            session_id=body.session_id,
            source_lang=body.source_lang,
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                detail="No se pudo registrar el correo. Intenta de nuevo.",
                error_code="LEAD_STORAGE_ERROR",
            ).model_dump(),
        )

    return DemoLeadResponse(status="received")
