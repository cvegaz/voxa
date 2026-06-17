"""Pydantic models for the audio transcription controls module."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Response for POST /api/transcriptions/transcribe."""

    transcription_id: UUID
    text: str


class AcceptRequest(BaseModel):
    """Request body for POST /api/transcriptions/accept."""

    transcription_id: UUID
    text: str = Field(min_length=1)


class AcceptResponse(BaseModel):
    """Response for POST /api/transcriptions/accept."""

    status: str  # "accepted"


class ResetRequest(BaseModel):
    """Request body for POST /api/transcriptions/reset."""

    transcription_id: UUID


class ResetResponse(BaseModel):
    """Response for POST /api/transcriptions/reset."""

    status: str  # "reset"


class TranscriptionSession(BaseModel):
    """Represents a persisted transcription session from the database."""

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
    """Standard error response for transcription endpoints."""

    detail: str
    error_code: str
