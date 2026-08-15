"""Tests for POST /api/demo-leads — the soft gate (ADR-0019 §5).

The behaviour worth pinning down is mostly what this endpoint **refuses to do**.
It is trivially easy to "improve" a lead form into a wall — make the field
required, grant a little extra quota for filling it, gate the download on it — and
every one of those changes breaks the design: the first two cost conversions at
the exact moment of maximum interest, and the third hands out quota for an
unverified string.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    app.state.pool = MagicMock()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def repo():
    with patch("app.routes.demo_lead_routes.DemoLeadRepository") as cls:
        cls.return_value.create_lead = AsyncMock(return_value=uuid4())
        yield cls.return_value


class TestDemoLeadCapture:
    def test_records_a_lead_from_the_download_step(self, client, repo):
        session_id = uuid4()

        response = client.post(
            "/api/demo-leads",
            json={
                "email": "alguien@ejemplo.com",
                "capturePoint": "download",
                "sessionId": str(session_id),
                "sourceLang": "es",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "received"
        repo.create_lead.assert_awaited_once_with(
            email="alguien@ejemplo.com",
            capture_point="download",
            session_id=session_id,
            source_lang="es",
        )

    def test_records_a_lead_from_the_wall(self, client, repo):
        """The higher-intent of the two moments: they narrated and want more."""
        response = client.post(
            "/api/demo-leads",
            json={"email": "alguien@ejemplo.com", "capturePoint": "wall"},
        )

        assert response.status_code == 200
        assert repo.create_lead.await_args.kwargs["capture_point"] == "wall"

    def test_works_without_a_session(self, client, repo):
        response = client.post(
            "/api/demo-leads",
            json={"email": "alguien@ejemplo.com", "capturePoint": "download"},
        )

        assert response.status_code == 200
        assert repo.create_lead.await_args.kwargs["session_id"] is None


class TestDemoLeadGrantsNothing:
    """The soft gate's defining property (ADR-0019 §5)."""

    def test_the_response_carries_no_token_quota_or_permission(self, client, repo):
        """An unverified address that buys anything is a Sybil hole.

        If this response ever grows a field that unlocks something, a visitor can
        mint themselves unlimited quota by typing a different address each time —
        strictly easier to abuse than the IP limit it would be replacing.
        """
        response = client.post(
            "/api/demo-leads",
            json={"email": "alguien@ejemplo.com", "capturePoint": "wall"},
        )

        assert response.json() == {"status": "received"}

    def test_capture_point_must_be_one_of_the_two_known_moments(self, client, repo):
        """A closed set, so the funnel report can compare them without guessing."""
        response = client.post(
            "/api/demo-leads",
            json={"email": "alguien@ejemplo.com", "capturePoint": "inventado"},
        )

        assert response.status_code == 422
        repo.create_lead.assert_not_awaited()


class TestDemoLeadValidation:
    @pytest.mark.parametrize(
        "email", ["sin-arroba", "@ejemplo.com", "a@b", "", "   "]
    )
    def test_rejects_a_malformed_address(self, client, repo, email):
        response = client.post(
            "/api/demo-leads",
            json={"email": email, "capturePoint": "download"},
        )

        assert response.status_code == 422
        # ADR-0005: flattened, never a nested detail.
        assert isinstance(response.json()["detail"], str)
        repo.create_lead.assert_not_awaited()

    def test_trims_surrounding_whitespace(self, client, repo):
        response = client.post(
            "/api/demo-leads",
            json={"email": "  alguien@ejemplo.com  ", "capturePoint": "download"},
        )

        assert response.status_code == 200
        assert repo.create_lead.await_args.kwargs["email"] == "alguien@ejemplo.com"

    def test_honeypot_submissions_are_dropped_silently(self, client, repo):
        """A bot must not be able to tell its entry was rejected.

        Same 200 and same body as a genuine submission — an error would teach the
        author of the bot exactly which field to stop filling.
        """
        response = client.post(
            "/api/demo-leads",
            json={
                "email": "bot@ejemplo.com",
                "capturePoint": "download",
                "website": "http://spam.example",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "received"
        repo.create_lead.assert_not_awaited()

    def test_storage_failure_returns_a_flattened_502(self, client, repo):
        repo.create_lead = AsyncMock(side_effect=RuntimeError("db down"))

        response = client.post(
            "/api/demo-leads",
            json={"email": "alguien@ejemplo.com", "capturePoint": "download"},
        )

        assert response.status_code == 502
        assert response.json()["errorCode"] == "LEAD_STORAGE_ERROR"
