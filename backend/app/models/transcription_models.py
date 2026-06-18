"""Pydantic models for the audio transcription controls module."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import CamelModel


class TranscribeResponse(CamelModel):
    """Response for POST /api/transcriptions/transcribe."""

    transcription_id: UUID
    text: str


class AcceptRequest(CamelModel):
    """Request body for POST /api/transcriptions/accept."""

    transcription_id: UUID
    text: str = Field(min_length=1)


class AcceptResponse(CamelModel):
    """Response for POST /api/transcriptions/accept."""

    status: str  # "accepted"


class ResetRequest(CamelModel):
    """Request body for POST /api/transcriptions/reset."""

    transcription_id: UUID


class ResetResponse(CamelModel):
    """Response for POST /api/transcriptions/reset."""

    status: str  # "reset"


class TranscriptionSession(CamelModel):
    """Represents a persisted transcription session (returned by GET /{id})."""

    id: UUID
    template_session_id: UUID
    status: str
    original_text: str
    final_text: Optional[str] = None
    duration_seconds: float
    created_at: datetime
    accepted_at: Optional[datetime] = None
    discarded_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Standard error response (internal shape; flattened by the API handler)."""

    detail: str
    error_code: str
