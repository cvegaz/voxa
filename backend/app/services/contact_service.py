"""Business logic for the landing-page contact form.

Responsibilities:
- Reject spam via the honeypot field (silently — bots get a 200 with no row).
- Trim/normalize the submitted values before persisting.
- Persist the message through the repository.
- Optionally notify the owner by email, if SMTP is configured (best-effort:
  a notification failure must never fail the user's submission).
"""

import os
import smtplib
from email.message import EmailMessage
from typing import Optional
from uuid import UUID

from ..models.contact_models import ContactRequest
from ..repositories.contact_repository import ContactRepository


class ContactService:
    """Validate, persist, and (optionally) notify about contact submissions."""

    def __init__(
        self,
        repository: ContactRepository,
        notify_email: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
    ) -> None:
        self._repository = repository
        # Fall back to environment variables so the route can construct the
        # service with just the repository (the same DI pattern used elsewhere).
        self._notify_email = notify_email or os.getenv("CONTACT_NOTIFY_EMAIL")
        self._smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self._smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self._smtp_user = smtp_user or os.getenv("SMTP_USER")
        self._smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")

    async def submit(self, payload: ContactRequest) -> Optional[UUID]:
        """Process a contact submission.

        Returns the new message ID, or ``None`` when the submission is treated
        as spam (honeypot filled). Spam is dropped silently so bots cannot tell
        their submission was rejected.
        """
        # Honeypot: a real (hidden) field that only bots fill in.
        if payload.website and payload.website.strip():
            return None

        name = payload.name.strip()
        email = payload.email.strip()
        message = payload.message.strip()
        company = payload.company.strip() if payload.company else None
        company = company or None
        source_lang = payload.source_lang.strip() if payload.source_lang else None
        source_lang = source_lang or None

        message_id = await self._repository.create_message(
            name=name,
            email=email,
            message=message,
            company=company,
            source_lang=source_lang,
        )

        self._notify(name=name, email=email, company=company, message=message)
        return message_id

    def _notify(
        self, name: str, email: str, company: Optional[str], message: str
    ) -> None:
        """Send an email notification if SMTP is configured (best-effort)."""
        if not (self._notify_email and self._smtp_host):
            return

        try:
            msg = EmailMessage()
            msg["Subject"] = f"Voxa — nuevo contacto de {name}"
            msg["From"] = self._smtp_user or self._notify_email
            msg["To"] = self._notify_email
            msg["Reply-To"] = email
            body = (
                f"Nombre: {name}\n"
                f"Email: {email}\n"
                f"Empresa: {company or '-'}\n\n"
                f"Mensaje:\n{message}\n"
            )
            msg.set_content(body)

            with smtplib.SMTP(self._smtp_host, self._smtp_port) as smtp:
                smtp.starttls()
                if self._smtp_user and self._smtp_password:
                    smtp.login(self._smtp_user, self._smtp_password)
                smtp.send_message(msg)
        except Exception:
            # Notification is best-effort: the message is already persisted, so
            # we never surface SMTP problems to the user.
            return
