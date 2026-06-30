"""Unit tests for POST /api/contact endpoint."""

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
    """Create a test client with a mocked database pool."""
    app.state.pool = mock_pool
    return TestClient(app, raise_server_exceptions=False)


def _valid_payload(**overrides):
    payload = {
        "name": "Carlos Vega",
        "email": "carlos@example.com",
        "company": "Acme",
        "message": "Me interesa adaptar Voxa a mi caso de uso.",
    }
    payload.update(overrides)
    return payload


class TestContactEndpointSuccess:
    @patch("app.routes.contact_routes.ContactService")
    @patch("app.routes.contact_routes.ContactRepository")
    def test_valid_submission_returns_200(self, MockRepo, MockService, client):
        new_id = uuid4()
        MockService.return_value.submit = AsyncMock(return_value=new_id)

        response = client.post("/api/contact", json=_valid_payload())

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["id"] == str(new_id)

    @patch("app.routes.contact_routes.ContactService")
    @patch("app.routes.contact_routes.ContactRepository")
    def test_camelcase_field_accepted(self, MockRepo, MockService, client):
        """sourceLang (camelCase alias) is accepted on the request body."""
        MockService.return_value.submit = AsyncMock(return_value=uuid4())

        response = client.post(
            "/api/contact", json=_valid_payload(sourceLang="es")
        )

        assert response.status_code == 200

    @patch("app.routes.contact_routes.ContactService")
    @patch("app.routes.contact_routes.ContactRepository")
    def test_honeypot_returns_200_without_id(self, MockRepo, MockService, client):
        """A filled honeypot is treated as spam: 200, but no persisted id."""
        # Service returns None to signal a silently-dropped spam submission.
        MockService.return_value.submit = AsyncMock(return_value=None)

        response = client.post(
            "/api/contact", json=_valid_payload(website="http://spam.example")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["id"] is None


class TestContactEndpointValidation:
    def test_invalid_email_returns_422(self, client):
        response = client.post(
            "/api/contact", json=_valid_payload(email="not-an-email")
        )
        assert response.status_code == 422
        data = response.json()
        # Flattened error contract: top-level detail + errorCode.
        assert data["errorCode"] == "VALIDATION_ERROR"
        assert isinstance(data["detail"], str)

    def test_missing_name_returns_422(self, client):
        payload = _valid_payload()
        del payload["name"]
        response = client.post("/api/contact", json=payload)
        assert response.status_code == 422

    def test_empty_message_returns_422(self, client):
        response = client.post("/api/contact", json=_valid_payload(message=""))
        assert response.status_code == 422


class TestContactEndpointFailure:
    @patch("app.routes.contact_routes.ContactService")
    @patch("app.routes.contact_routes.ContactRepository")
    def test_persist_failure_returns_502(self, MockRepo, MockService, client):
        MockService.return_value.submit = AsyncMock(
            side_effect=RuntimeError("db down")
        )

        response = client.post("/api/contact", json=_valid_payload())

        assert response.status_code == 502
        data = response.json()
        assert data["errorCode"] == "CONTACT_PERSIST_FAILED"
