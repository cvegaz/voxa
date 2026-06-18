"""Unit tests for GET /api/templates/active endpoint."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ColumnDef, ColumnSchema, TemplateSession


def _make_confirmed_session(
    session_id=None,
    file_name="plantilla.xlsx",
    enriched_context="Contexto enriquecido por LLM con detalles adicionales.",
    confirmed_at=None,
):
    """Create a TemplateSession representing a confirmed session."""
    if session_id is None:
        session_id = uuid4()
    if confirmed_at is None:
        confirmed_at = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)

    schema = ColumnSchema(
        columns=[
            ColumnDef(index=1, name="Nombre", data_type="texto", example_value="Juan"),
            ColumnDef(index=2, name="Edad", data_type="número", example_value="30"),
        ]
    )

    return TemplateSession(
        id=session_id,
        status="confirmed",
        column_schema=schema,
        dataframe_json='[{"Nombre": "Juan", "Edad": 30}]',
        user_context="Contexto original del usuario con suficiente longitud.",
        enriched_context=enriched_context,
        file_name=file_name,
        column_count=2,
        created_at=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        confirmed_at=confirmed_at,
        replaced_at=None,
    )


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    pool = MagicMock()
    return pool


@pytest.fixture
def client(mock_pool):
    """Create a test client with mocked database pool."""
    app.state.pool = mock_pool
    return TestClient(app, raise_server_exceptions=False)


class TestGetActiveSessionSuccess:
    """Tests for successful GET /api/templates/active."""

    def test_returns_active_session(self, client, mock_pool):
        """Returns 200 with active session data when a confirmed session exists."""
        session = _make_confirmed_session()

        with patch(
            "app.routes.template_routes.TemplateRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_active_session.return_value = session
            MockRepo.return_value = mock_repo_instance

            response = client.get("/api/templates/active")

        assert response.status_code == 200
        data = response.json()
        assert data["sessionId"] == str(session.id)
        assert data["fileName"] == "plantilla.xlsx"
        assert data["enrichedContext"] == session.enriched_context
        assert "confirmedAt" in data

    def test_response_contains_schema(self, client, mock_pool):
        """Response includes the column schema with correct structure."""
        session = _make_confirmed_session()

        with patch(
            "app.routes.template_routes.TemplateRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_active_session.return_value = session
            MockRepo.return_value = mock_repo_instance

            response = client.get("/api/templates/active")

        assert response.status_code == 200
        schema = response.json()["schema"]
        assert "columns" in schema
        assert len(schema["columns"]) == 2
        assert schema["columns"][0]["name"] == "Nombre"
        assert schema["columns"][1]["name"] == "Edad"

    def test_response_schema_columns_have_all_fields(self, client, mock_pool):
        """Each column in the response schema has index, name, data_type, example_value."""
        session = _make_confirmed_session()

        with patch(
            "app.routes.template_routes.TemplateRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_active_session.return_value = session
            MockRepo.return_value = mock_repo_instance

            response = client.get("/api/templates/active")

        columns = response.json()["schema"]["columns"]
        for col in columns:
            assert "index" in col
            assert "name" in col
            assert "dataType" in col
            assert "exampleValue" in col

    def test_confirmed_at_is_iso_format(self, client, mock_pool):
        """confirmed_at is returned as an ISO 8601 datetime string."""
        confirmed_at = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        session = _make_confirmed_session(confirmed_at=confirmed_at)

        with patch(
            "app.routes.template_routes.TemplateRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_active_session.return_value = session
            MockRepo.return_value = mock_repo_instance

            response = client.get("/api/templates/active")

        assert response.status_code == 200
        # Should be parseable as a datetime
        confirmed_at_str = response.json()["confirmedAt"]
        # Python 3.10 fromisoformat doesn't support 'Z' suffix; replace with +00:00
        parsed = datetime.fromisoformat(confirmed_at_str.replace("Z", "+00:00"))
        assert parsed.year == 2024
        assert parsed.month == 6
        assert parsed.day == 15


class TestGetActiveSessionNotFound:
    """Tests for 404 when no active session exists."""

    def test_returns_404_when_no_active_session(self, client, mock_pool):
        """Returns 404 with SESSION_NOT_FOUND when no confirmed session exists."""
        with patch(
            "app.routes.template_routes.TemplateRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_active_session.return_value = None
            MockRepo.return_value = mock_repo_instance

            response = client.get("/api/templates/active")

        assert response.status_code == 404
        assert response.json()["errorCode"] == "SESSION_NOT_FOUND"

    def test_404_response_has_detail_message(self, client, mock_pool):
        """404 response includes a descriptive detail message."""
        with patch(
            "app.routes.template_routes.TemplateRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_active_session.return_value = None
            MockRepo.return_value = mock_repo_instance

            response = client.get("/api/templates/active")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        assert len(detail) > 0
