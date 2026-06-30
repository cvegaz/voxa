"""Unit tests for ContactService (honeypot, normalization, optional email)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.contact_models import ContactRequest
from app.services.contact_service import ContactService


def _request(**overrides) -> ContactRequest:
    data = {
        "name": "  Carlos Vega  ",
        "email": "  carlos@example.com ",
        "company": "  Acme  ",
        "message": "  Hola, me interesa Voxa.  ",
    }
    data.update(overrides)
    return ContactRequest(**data)


@pytest.fixture
def repository():
    repo = MagicMock()
    repo.create_message = AsyncMock(return_value=uuid4())
    return repo


class TestSubmit:
    @pytest.mark.asyncio
    async def test_persists_trimmed_values(self, repository):
        service = ContactService(repository)

        result = await service.submit(_request())

        assert result is not None
        repository.create_message.assert_awaited_once()
        kwargs = repository.create_message.await_args.kwargs
        assert kwargs["name"] == "Carlos Vega"
        assert kwargs["email"] == "carlos@example.com"
        assert kwargs["company"] == "Acme"
        assert kwargs["message"] == "Hola, me interesa Voxa."

    @pytest.mark.asyncio
    async def test_blank_company_becomes_none(self, repository):
        service = ContactService(repository)

        await service.submit(_request(company="   "))

        kwargs = repository.create_message.await_args.kwargs
        assert kwargs["company"] is None

    @pytest.mark.asyncio
    async def test_honeypot_filled_drops_submission(self, repository):
        service = ContactService(repository)

        result = await service.submit(_request(website="http://spam.example"))

        assert result is None
        repository.create_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_email_sent_when_smtp_unconfigured(self, repository):
        service = ContactService(repository)  # no SMTP env / args

        with patch("app.services.contact_service.smtplib.SMTP") as MockSMTP:
            await service.submit(_request())
            MockSMTP.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_sent_when_smtp_configured(self, repository):
        service = ContactService(
            repository,
            notify_email="owner@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
        )

        with patch("app.services.contact_service.smtplib.SMTP") as MockSMTP:
            smtp_instance = MockSMTP.return_value.__enter__.return_value
            await service.submit(_request())
            smtp_instance.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_failure_does_not_break_submit(self, repository):
        service = ContactService(
            repository,
            notify_email="owner@example.com",
            smtp_host="smtp.example.com",
        )

        with patch(
            "app.services.contact_service.smtplib.SMTP",
            side_effect=OSError("connection refused"),
        ):
            # Persistence already happened; the SMTP failure must be swallowed.
            result = await service.submit(_request())

        assert result is not None
        repository.create_message.assert_awaited_once()
