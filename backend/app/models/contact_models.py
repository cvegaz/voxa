"""Pydantic models for the public landing-page contact form (POST /api/contact)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from .base import CamelModel

# A pragmatic email shape check. We deliberately avoid the optional
# ``email-validator`` dependency (and its DNS-ish strictness) for a marketing
# form: a structural regex is enough to reject obvious garbage, and the service
# trims/limits everything before persisting.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class ContactRequest(CamelModel):
    """Request body for POST /api/contact.

    ``website`` is a honeypot: it is rendered hidden in the form, so a real
    human never fills it. If it arrives non-empty, the submission is treated as
    spam (see ContactService).
    """

    # Trim incoming strings before validation so a value like " a@b.co " passes
    # the email pattern and a whitespace-only message is rejected by min_length.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254, pattern=EMAIL_PATTERN)
    message: str = Field(min_length=1, max_length=4000)
    company: Optional[str] = Field(default=None, max_length=120)
    source_lang: Optional[str] = Field(default=None, max_length=5)
    # Honeypot — must stay empty. Optional so legitimate clients can omit it.
    website: Optional[str] = Field(default=None, max_length=255)


class ContactResponse(CamelModel):
    """Response for POST /api/contact."""

    id: Optional[UUID] = None
    status: str  # "received"


class ContactMessage(CamelModel):
    """A persisted contact message (internal shape)."""

    id: UUID
    name: str
    email: str
    company: Optional[str] = None
    message: str
    source_lang: Optional[str] = None
    created_at: datetime
