"""Pydantic models for the Excel template loader module."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import CamelModel


class ColumnDef(CamelModel):
    """Represents a single column definition from the Excel template."""

    index: int = Field(ge=1, le=8)
    name: str
    data_type: str
    example_value: str


class ColumnSchema(CamelModel):
    """Represents the full column schema extracted from the Excel template."""

    columns: list[ColumnDef] = Field(min_length=1, max_length=8)


class TemplateSession(BaseModel):
    """Represents a persisted template session from the database.

    Internal model (not serialized to the API), so it keeps snake_case.
    """

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


class UploadResponse(CamelModel):
    """Response for POST /api/templates/upload."""

    session_id: UUID
    # Explicit alias "schema" overrides the camelCase generator (would be
    # "columnSchema"); the frontend expects the field named "schema".
    column_schema: ColumnSchema = Field(alias="schema")
    file_name: str


class ConfirmRequest(CamelModel):
    """Request body for POST /api/templates/confirm."""

    session_id: UUID
    context: str


class ConfirmResponse(CamelModel):
    """Response for POST /api/templates/confirm."""

    enriched_context: str


class ActiveSessionResponse(CamelModel):
    """Response for GET /api/templates/active."""

    session_id: UUID
    column_schema: ColumnSchema = Field(alias="schema")
    enriched_context: str
    file_name: str
    confirmed_at: datetime


class ValidationResult(BaseModel):
    """Result of a file or context validation operation. Internal model."""

    is_valid: bool
    error_code: Optional[str] = None
    detail: Optional[str] = None
    affected_columns: Optional[list[str]] = None


class ErrorResponse(BaseModel):
    """Standard error response (internal shape; flattened by the API handler)."""

    detail: str
    error_code: str
