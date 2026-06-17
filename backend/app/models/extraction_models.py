"""Pydantic models for the LLM extraction module."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    """Request body for POST /api/extraction/process."""

    session_id: UUID
    transcribed_text: str = Field(min_length=1)


class RecordValue(BaseModel):
    """A single extracted value for a column."""

    column_name: str
    value: str  # string vacío si no se identificó


class ExtractionResult(BaseModel):
    """Response for a successful extraction process."""

    extraction_id: UUID
    record: list[RecordValue]
    row_number: int = Field(ge=4)


class ExtractionRecord(BaseModel):
    """A persisted extraction record returned in listing endpoints."""

    extraction_id: UUID
    row_number: int
    record: list[RecordValue]
    transcribed_text: str
    created_at: datetime


class RecordsResponse(BaseModel):
    """Response for GET /api/extraction/records/{session_id}."""

    records: list[ExtractionRecord]
    total_rows: int


class ErrorResponse(BaseModel):
    """Standard error response for extraction endpoints."""

    detail: str
    error_code: str
