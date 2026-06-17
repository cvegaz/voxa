"""Unit tests for AcceptanceValidator service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.transcription_models import TranscriptionSession

# Directly import the module to avoid services/__init__.py loading whisper_service
# which requires 'openai' that has circular import issues in this environment.
import importlib
import importlib.util
import sys

_spec = importlib.util.spec_from_file_location(
    "acceptance_validator",
    "app/services/acceptance_validator.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
AcceptanceValidator = _mod.AcceptanceValidator


@pytest.fixture
def mock_transcription_repo():
    """Create a mock TranscriptionRepository."""
    return AsyncMock()


@pytest.fixture
def mock_template_repo():
    """Create a mock TemplateRepository."""
    return AsyncMock()


@pytest.fixture
def validator(mock_transcription_repo, mock_template_repo):
    """Create an AcceptanceValidator with mocked dependencies."""
    return AcceptanceValidator(
        transcription_repository=mock_transcription_repo,
        template_repository=mock_template_repo,
    )


def _make_pending_session(transcription_id=None):
    """Helper to create a mock pending TranscriptionSession."""
    return TranscriptionSession(
        id=transcription_id or uuid4(),
        template_session_id=uuid4(),
        status="pending",
        original_text="some transcribed text",
        final_text=None,
        duration_seconds=5.0,
        created_at=datetime.now(timezone.utc),
        accepted_at=None,
        discarded_at=None,
    )


def _make_accepted_session(transcription_id=None):
    """Helper to create a mock accepted TranscriptionSession."""
    return TranscriptionSession(
        id=transcription_id or uuid4(),
        template_session_id=uuid4(),
        status="accepted",
        original_text="some transcribed text",
        final_text="final text",
        duration_seconds=5.0,
        created_at=datetime.now(timezone.utc),
        accepted_at=datetime.now(timezone.utc),
        discarded_at=None,
    )


class TestAcceptanceValidatorSessionNotFound:
    """Tests for SESSION_NOT_FOUND error code."""

    @pytest.mark.asyncio
    async def test_session_not_found_returns_error(
        self, validator, mock_transcription_repo
    ):
        """Validation fails when session does not exist."""
        mock_transcription_repo.get_session.return_value = None

        result = await validator.validate(uuid4(), "some text")

        assert result.is_valid is False
        assert result.error_code == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_session_not_pending_returns_error(
        self, validator, mock_transcription_repo
    ):
        """Validation fails when session exists but is not in pending status."""
        session = _make_accepted_session()
        mock_transcription_repo.get_session.return_value = session

        result = await validator.validate(session.id, "some text")

        assert result.is_valid is False
        assert result.error_code == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_session_discarded_returns_error(
        self, validator, mock_transcription_repo
    ):
        """Validation fails when session is in discarded status."""
        session_id = uuid4()
        discarded_session = TranscriptionSession(
            id=session_id,
            template_session_id=uuid4(),
            status="discarded",
            original_text="text",
            final_text=None,
            duration_seconds=3.0,
            created_at=datetime.now(timezone.utc),
            accepted_at=None,
            discarded_at=datetime.now(timezone.utc),
        )
        mock_transcription_repo.get_session.return_value = discarded_session

        result = await validator.validate(session_id, "some text")

        assert result.is_valid is False
        assert result.error_code == "SESSION_NOT_FOUND"


class TestAcceptanceValidatorEmptyTranscription:
    """Tests for EMPTY_TRANSCRIPTION error code."""

    @pytest.mark.asyncio
    async def test_empty_string_returns_error(
        self, validator, mock_transcription_repo
    ):
        """Validation fails when text is an empty string."""
        session = _make_pending_session()
        mock_transcription_repo.get_session.return_value = session

        result = await validator.validate(session.id, "")

        assert result.is_valid is False
        assert result.error_code == "EMPTY_TRANSCRIPTION"

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_error(
        self, validator, mock_transcription_repo
    ):
        """Validation fails when text is only whitespace."""
        session = _make_pending_session()
        mock_transcription_repo.get_session.return_value = session

        result = await validator.validate(session.id, "   \t\n  ")

        assert result.is_valid is False
        assert result.error_code == "EMPTY_TRANSCRIPTION"

    @pytest.mark.asyncio
    async def test_tabs_and_newlines_only_returns_error(
        self, validator, mock_transcription_repo
    ):
        """Validation fails when text is only tabs and newlines."""
        session = _make_pending_session()
        mock_transcription_repo.get_session.return_value = session

        result = await validator.validate(session.id, "\t\t\n\n")

        assert result.is_valid is False
        assert result.error_code == "EMPTY_TRANSCRIPTION"


class TestAcceptanceValidatorNoConfirmedSchema:
    """Tests for NO_CONFIRMED_SCHEMA error code."""

    @pytest.mark.asyncio
    async def test_no_active_session_returns_error(
        self, validator, mock_transcription_repo, mock_template_repo
    ):
        """Validation fails when no confirmed template session exists."""
        session = _make_pending_session()
        mock_transcription_repo.get_session.return_value = session
        mock_template_repo.get_active_session.return_value = None

        result = await validator.validate(session.id, "valid text")

        assert result.is_valid is False
        assert result.error_code == "NO_CONFIRMED_SCHEMA"


class TestAcceptanceValidatorSuccess:
    """Tests for successful validation."""

    @pytest.mark.asyncio
    async def test_valid_acceptance(
        self, validator, mock_transcription_repo, mock_template_repo
    ):
        """Validation succeeds with pending session, non-empty text, and confirmed schema."""
        session = _make_pending_session()
        mock_transcription_repo.get_session.return_value = session
        mock_template_repo.get_active_session.return_value = MagicMock()  # any non-None value

        result = await validator.validate(session.id, "Hoy compramos 5 cajas")

        assert result.is_valid is True
        assert result.error_code is None
        assert result.detail is None

    @pytest.mark.asyncio
    async def test_valid_acceptance_with_edited_text(
        self, validator, mock_transcription_repo, mock_template_repo
    ):
        """Validation succeeds with edited text that has leading/trailing spaces but content."""
        session = _make_pending_session()
        mock_transcription_repo.get_session.return_value = session
        mock_template_repo.get_active_session.return_value = MagicMock()

        result = await validator.validate(session.id, "  texto editado  ")

        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_valid_acceptance_single_char(
        self, validator, mock_transcription_repo, mock_template_repo
    ):
        """Validation succeeds with a single non-whitespace character."""
        session = _make_pending_session()
        mock_transcription_repo.get_session.return_value = session
        mock_template_repo.get_active_session.return_value = MagicMock()

        result = await validator.validate(session.id, "a")

        assert result.is_valid is True


class TestAcceptanceValidatorPriority:
    """Tests for validation priority/order."""

    @pytest.mark.asyncio
    async def test_session_check_happens_before_text_check(
        self, validator, mock_transcription_repo
    ):
        """SESSION_NOT_FOUND is returned even when text is empty (checked first)."""
        mock_transcription_repo.get_session.return_value = None

        result = await validator.validate(uuid4(), "")

        assert result.error_code == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_text_check_happens_before_schema_check(
        self, validator, mock_transcription_repo, mock_template_repo
    ):
        """EMPTY_TRANSCRIPTION is returned even when no schema exists (checked before schema)."""
        session = _make_pending_session()
        mock_transcription_repo.get_session.return_value = session
        mock_template_repo.get_active_session.return_value = None

        result = await validator.validate(session.id, "   ")

        assert result.error_code == "EMPTY_TRANSCRIPTION"
