"""Pydantic models for the Excel template loader module."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ColumnDef(BaseModel):
    """Represents a single column definition from the Excel template."""

    index: int = Field(ge=1, le=8)
    name: str
    data_type: str
    example_value: str


class ColumnSchema(BaseModel):
    """Represents the full column schema extracted from the Excel template."""

    columns: list[ColumnDef] = Field(min_length=1, max_length=8)


class TemplateSession(BaseModel):
    """Represents a persisted template session from the database."""

    id: UUID
    status: str
    column_schema: ColumnSchema = Field(alias="schema_json")
    dataframe_json: str
    user_context: Optional[str] = None
    enriched_context: Optional[str] = None
    file_name: str
    column_count: int
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    replaced_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class UploadResponse(BaseModel):
    """Response for POST /api/templates/upload."""

    session_id: UUID
    column_schema: ColumnSchema = Field(alias="schema")
    file_name: str

    model_config = {"populate_by_name": True}


class ConfirmRequest(BaseModel):
    """Request body for POST /api/templates/confirm."""

    session_id: UUID
    context: str


class ConfirmResponse(BaseModel):
    """Response for POST /api/templates/confirm."""

    enriched_context: str


class ActiveSessionResponse(BaseModel):
    """Response for GET /api/templates/active."""

    session_id: UUID
    column_schema: ColumnSchema = Field(alias="schema")
    enriched_context: str
    file_name: str
    confirmed_at: datetime

    model_config = {"populate_by_name": True}


class ValidationResult(BaseModel):
    """Result of a file or context validation operation."""

    is_valid: bool
    error_code: Optional[str] = None
    detail: Optional[str] = None
    affected_columns: Optional[list[str]] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: str
