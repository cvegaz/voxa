"""Unit tests for GET /api/extraction/records/{session_id} endpoint."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    return MagicMock()


@pytest.fixture
def client(mock_pool):
    """Create a test client with mocked database pool."""
    app.state.pool = mock_pool
    return TestClient(app, raise_server_exceptions=False)


class TestGetExtractionRecordsEmpty:
    """Tests for GET /api/extraction/records/{session_id} with no records."""

    def test_returns_empty_list_for_session_with_no_records(self, client, mock_pool):
        """Returns 200 with empty records list and total_rows=0 when no records exist."""
        session_id = uuid4()

        with patch(
            "app.routes.extraction_routes.ExtractionRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_records.return_value = []
            MockRepo.return_value = mock_repo_instance

            response = client.get(f"/api/extraction/records/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["records"] == []
        assert data["total_rows"] == 0


class TestGetExtractionRecordsWithData:
    """Tests for GET /api/extraction/records/{session_id} with existing records."""

    def test_returns_correct_records_with_total_rows(self, client, mock_pool):
        """Returns 200 with records list and correct total_rows count."""
        session_id = uuid4()
        extraction_id_1 = uuid4()
        extraction_id_2 = uuid4()
        created_at = datetime(2024, 7, 10, 14, 0, 0, tzinfo=timezone.utc)

        mock_records = [
            {
                "id": str(extraction_id_1),
                "session_id": str(session_id),
                "row_number": 4,
                "record_json": {"Nombre": "Juan", "Edad": "30"},
                "transcribed_text": "Me llamo Juan y tengo 30 años",
                "status": "completed",
                "error_message": None,
                "created_at": created_at,
            },
            {
                "id": str(extraction_id_2),
                "session_id": str(session_id),
                "row_number": 5,
                "record_json": {"Nombre": "María", "Edad": "25"},
                "transcribed_text": "Soy María, tengo 25 años",
                "status": "completed",
                "error_message": None,
                "created_at": created_at,
            },
        ]

        with patch(
            "app.routes.extraction_routes.ExtractionRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_records.return_value = mock_records
            MockRepo.return_value = mock_repo_instance

            response = client.get(f"/api/extraction/records/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 2
        assert len(data["records"]) == 2

        # Verify first record
        rec1 = data["records"][0]
        assert rec1["extraction_id"] == str(extraction_id_1)
        assert rec1["row_number"] == 4
        assert rec1["transcribed_text"] == "Me llamo Juan y tengo 30 años"

        # Verify second record
        rec2 = data["records"][1]
        assert rec2["extraction_id"] == str(extraction_id_2)
        assert rec2["row_number"] == 5
        assert rec2["transcribed_text"] == "Soy María, tengo 25 años"

    def test_record_json_is_correctly_mapped_to_record_value_list(
        self, client, mock_pool
    ):
        """record_json dict is transformed into a list of RecordValue objects."""
        session_id = uuid4()
        extraction_id = uuid4()
        created_at = datetime(2024, 7, 10, 14, 0, 0, tzinfo=timezone.utc)

        mock_records = [
            {
                "id": str(extraction_id),
                "session_id": str(session_id),
                "row_number": 4,
                "record_json": {"Nombre": "Juan", "Edad": "30", "Ciudad": "Madrid"},
                "transcribed_text": "Soy Juan, 30 años, de Madrid",
                "status": "completed",
                "error_message": None,
                "created_at": created_at,
            },
        ]

        with patch(
            "app.routes.extraction_routes.ExtractionRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_records.return_value = mock_records
            MockRepo.return_value = mock_repo_instance

            response = client.get(f"/api/extraction/records/{session_id}")

        assert response.status_code == 200
        data = response.json()
        record = data["records"][0]["record"]

        # Should be a list of {column_name, value} objects
        assert isinstance(record, list)
        assert len(record) == 3

        # Verify each value is mapped correctly
        record_dict = {rv["column_name"]: rv["value"] for rv in record}
        assert record_dict["Nombre"] == "Juan"
        assert record_dict["Edad"] == "30"
        assert record_dict["Ciudad"] == "Madrid"

    def test_record_values_have_correct_structure(self, client, mock_pool):
        """Each RecordValue in the record list has column_name and value fields."""
        session_id = uuid4()
        extraction_id = uuid4()
        created_at = datetime(2024, 7, 10, 14, 0, 0, tzinfo=timezone.utc)

        mock_records = [
            {
                "id": str(extraction_id),
                "session_id": str(session_id),
                "row_number": 4,
                "record_json": {"Nombre": "Ana"},
                "transcribed_text": "Me llamo Ana",
                "status": "completed",
                "error_message": None,
                "created_at": created_at,
            },
        ]

        with patch(
            "app.routes.extraction_routes.ExtractionRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_records.return_value = mock_records
            MockRepo.return_value = mock_repo_instance

            response = client.get(f"/api/extraction/records/{session_id}")

        assert response.status_code == 200
        record_values = data = response.json()["records"][0]["record"]
        for rv in record_values:
            assert "column_name" in rv
            assert "value" in rv
