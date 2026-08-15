"""Pydantic models for demo lead capture (POST /api/demo-leads, ADR-0019 §5)."""

from typing import Literal, Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from .base import CamelModel
from .contact_models import EMAIL_PATTERN

# The two moments where an address is asked for. A closed set rather than free
# text, so the funnel report can compare them without normalising strings later.
CapturePoint = Literal["download", "wall"]


class DemoLeadRequest(CamelModel):
    """Request body for POST /api/demo-leads.

    ``website`` is a honeypot, same as the contact form: rendered hidden, so a
    real human never fills it.

    Note what is NOT here: no name, no company, no message. An address given on
    the way out of a demo is worth its own weight and nothing more — every extra
    required field costs conversions at the exact moment the visitor is deciding
    whether you are worth the typing.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=254, pattern=EMAIL_PATTERN)
    capture_point: CapturePoint
    session_id: Optional[UUID] = None
    source_lang: Optional[str] = Field(default=None, max_length=5)
    # Honeypot — must stay empty.
    website: Optional[str] = Field(default=None, max_length=255)


class DemoLeadResponse(CamelModel):
    """Response for POST /api/demo-leads.

    Carries no quota, no token, no permission — deliberately (ADR-0019 §5). An
    unverified address that buys anything is a Sybil hole: type a new one, get
    more. The only thing this endpoint grants is a record that somebody was
    interested.
    """

    status: str  # "received"
