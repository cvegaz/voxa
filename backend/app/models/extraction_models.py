"""Pydantic models for the LLM extraction module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .base import CamelModel


class ExtractionRequest(CamelModel):
    """Request body for POST /api/extraction/process."""

    session_id: UUID
    transcribed_text: str = Field(min_length=1)


class RecordValue(CamelModel):
    """A single extracted value for a column."""

    column_name: str
    value: str  # empty string if it could not be identified


class ExtractionResult(CamelModel):
    """Response for a successful extraction process."""

    extraction_id: UUID
    record: list[RecordValue]
    row_number: int = Field(ge=4)


class ExtractionRecord(CamelModel):
    """A persisted extraction record returned in listing endpoints."""

    extraction_id: UUID
    row_number: int
    record: list[RecordValue]
    transcribed_text: str
    created_at: datetime


class RecordsResponse(CamelModel):
    """Response for GET /api/extraction/records/{session_id}."""

    records: list[ExtractionRecord]
    total_rows: int


class ErrorResponse(BaseModel):
    """Standard error response (internal shape; flattened by the API handler)."""

    detail: str
    error_code: str
