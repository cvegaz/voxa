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
    # First data record lands on row 2 (row 1 is the single header row — ADR-0013).
    row_number: int = Field(ge=2)


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
    # Capture cap and whether the session is closed (ADR-0013). The UI uses these
    # to show "N / max_rows" and to enable the download / disable capture.
    max_rows: int
    finalized: bool


class FinalizeResponse(CamelModel):
    """Response for POST /api/extraction/finalize/{session_id}."""

    status: str  # always "finalized"
    total_rows: int


class ErrorResponse(BaseModel):
    """Standard error response (internal shape; flattened by the API handler)."""

    detail: str
    error_code: str
