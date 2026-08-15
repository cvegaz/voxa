"""Tests for the public demo's spend ceilings (ADR-0019 §3).

The ledger is faked with a faithful in-memory implementation — it stores timestamped
entries and really sums them by window — so the day/month boundary logic is under
test rather than mocked away. The clock is injected, because a budget that resets
"tomorrow" is untestable if you have to wait for tomorrow.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.exceptions import DemoBudgetExhaustedError
from app.services.usage_budget import (
    OPERATION_ENRICHMENT,
    OPERATION_EXTRACTION,
    OPERATION_TRANSCRIPTION,
    UsageBudget,
)

NOW = datetime(2026, 8, 14, 15, 30, tzinfo=timezone.utc)


class FakeLedger:
    """In-memory stand-in for UsageRepository that really filters by instant."""

    def __init__(self, entries: list[tuple[datetime, str]] | None = None):
        # (when, cost) — cost as str so the Decimal is exact, like the DB column.
        self.entries = [(when, Decimal(cost)) for when, cost in (entries or [])]
        self.recorded: list[tuple[str, Decimal, object]] = []

    async def record(self, operation, estimated_cost_usd, session_id=None):
        self.recorded.append((operation, estimated_cost_usd, session_id))
        self.entries.append((NOW, estimated_cost_usd))

    async def spent_since(self, instant):
        return sum(
            (cost for when, cost in self.entries if when >= instant), Decimal("0")
        )


def _budget(ledger: FakeLedger, now: datetime = NOW) -> UsageBudget:
    return UsageBudget(ledger, clock=lambda: now)


class TestBudgetAllows:
    @pytest.mark.asyncio
    async def test_passes_on_an_empty_ledger(self):
        await _budget(FakeLedger()).check()  # must not raise

    @pytest.mark.asyncio
    async def test_passes_while_under_both_ceilings(self):
        ledger = FakeLedger([(NOW - timedelta(hours=1), "0.20")])
        await _budget(ledger).check()


class TestDailyCeiling:
    @pytest.mark.asyncio
    async def test_blocks_once_the_day_is_spent(self, monkeypatch):
        monkeypatch.setattr("app.services.usage_budget.DEMO_BUDGET_DAILY_USD", 0.45)
        ledger = FakeLedger([(NOW - timedelta(hours=2), "0.45")])

        with pytest.raises(DemoBudgetExhaustedError) as exc:
            await _budget(ledger).check()

        assert exc.value.error_code == "DEMO_BUDGET_EXHAUSTED"
        assert "hoy" in exc.value.detail

    @pytest.mark.asyncio
    async def test_yesterdays_spend_does_not_count_today(self, monkeypatch):
        """The window is the calendar day, not a rolling 24 h.

        An entry from 23:00 yesterday is outside today's window even though it is
        barely 16 hours old — that is what makes the budget heal at midnight.
        """
        monkeypatch.setattr("app.services.usage_budget.DEMO_BUDGET_DAILY_USD", 0.45)
        yesterday_late = NOW.replace(hour=23, minute=0) - timedelta(days=1)
        ledger = FakeLedger([(yesterday_late, "5.00")])

        await _budget(ledger).check()  # must not raise

    @pytest.mark.asyncio
    async def test_spend_earlier_today_does_count(self, monkeypatch):
        monkeypatch.setattr("app.services.usage_budget.DEMO_BUDGET_DAILY_USD", 0.45)
        ledger = FakeLedger([(NOW.replace(hour=0, minute=1), "0.50")])

        with pytest.raises(DemoBudgetExhaustedError):
            await _budget(ledger).check()


class TestMonthlyCeiling:
    @pytest.mark.asyncio
    async def test_blocks_even_when_the_day_is_fresh(self, monkeypatch):
        """The monthly ceiling is the real stop.

        A month that saturates goes quiet before day 30 by design: the daily cap is
        deliberately above monthly/30 so a good day is not punished, which means the
        month can run out early. Running out is a demand signal, not a bug.
        """
        monkeypatch.setattr("app.services.usage_budget.DEMO_BUDGET_DAILY_USD", 0.45)
        monkeypatch.setattr("app.services.usage_budget.DEMO_BUDGET_MONTHLY_USD", 7.00)
        # Spent across earlier days this month; nothing yet today.
        ledger = FakeLedger([(NOW.replace(day=2), "7.00")])

        with pytest.raises(DemoBudgetExhaustedError) as exc:
            await _budget(ledger).check()

        assert "mes" in exc.value.detail

    @pytest.mark.asyncio
    async def test_last_months_spend_does_not_count(self, monkeypatch):
        """One hour before the month starts — i.e. 23:00 on the last day of July.

        Note the boundary is the first instant of day 1, not "same time on day 1":
        an entry at 14:30 on August 1st is still inside August.
        """
        monkeypatch.setattr("app.services.usage_budget.DEMO_BUDGET_MONTHLY_USD", 7.00)
        month_start = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ledger = FakeLedger([(month_start - timedelta(hours=1), "50.00")])

        await _budget(ledger).check()


class TestRecording:
    @pytest.mark.asyncio
    async def test_charges_the_configured_unit_cost(self, monkeypatch):
        monkeypatch.setattr("app.services.usage_budget.DEMO_COST_TRANSCRIPTION", 0.0020)
        ledger = FakeLedger()
        session_id = uuid4()

        await _budget(ledger).record(OPERATION_TRANSCRIPTION, session_id=session_id)

        assert ledger.recorded == [
            (OPERATION_TRANSCRIPTION, Decimal("0.0020"), session_id)
        ]

    @pytest.mark.asyncio
    async def test_unit_costs_are_configuration(self, monkeypatch):
        """A price change must be an .env edit, not a release (ADR-0019 §4)."""
        monkeypatch.setattr("app.services.usage_budget.DEMO_COST_EXTRACTION", 0.0099)
        ledger = FakeLedger()

        await _budget(ledger).record(OPERATION_EXTRACTION)

        assert ledger.recorded[0][1] == Decimal("0.0099")

    @pytest.mark.asyncio
    async def test_costs_are_exact_decimals_not_floats(self, monkeypatch):
        """This column gets SUMmed thousands of times.

        Binary floating point accumulates representation error on exactly that
        operation, which is why the ledger stores NUMERIC and the service converts
        through str: `Decimal(0.0004)` would smuggle the float's error into what is
        meant to be exact decimal arithmetic.
        """
        monkeypatch.setattr("app.services.usage_budget.DEMO_COST_ENRICHMENT", 0.0005)
        ledger = FakeLedger()

        await _budget(ledger).record(OPERATION_ENRICHMENT)

        assert ledger.recorded[0][1] == Decimal("0.0005")

    @pytest.mark.asyncio
    async def test_rejects_an_unknown_operation(self):
        with pytest.raises(ValueError, match="Unknown billable operation"):
            await _budget(FakeLedger()).record("mining_bitcoin")


@pytest.fixture
def client():
    app.state.pool = MagicMock()
    return TestClient(app, raise_server_exceptions=False)


class TestBudgetAtTheEndpoint:
    """The ceiling has to reach the caller in the shape the frontend expects."""

    @patch("app.routes.transcription_routes.AudioDurationProbe")
    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_exhausted_budget_returns_a_flattened_429(
        self, mock_tmpl_repo_cls, mock_probe_cls, client, stub_usage_ledger
    ):
        stub_usage_ledger.spent = Decimal("999")
        mock_probe_cls.return_value.measure_seconds = AsyncMock(return_value=5.0)
        mock_tmpl_repo_cls.return_value.get_active_session = AsyncMock(
            return_value=MagicMock(id=uuid4(), language="es")
        )

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("a.webm", b"\x00\x01\x02", "audio/webm")},
        )

        body = response.json()
        assert response.status_code == 429
        assert body["errorCode"] == "DEMO_BUDGET_EXHAUSTED"
        # ADR-0005: never a nested detail, never snake_case.
        assert isinstance(body["detail"], str)

    @patch("app.routes.transcription_routes.WhisperTranscriptionService")
    @patch("app.routes.transcription_routes.AudioDurationProbe")
    @patch("app.routes.transcription_routes.TemplateRepository")
    def test_a_failed_openai_call_does_not_consume_budget(
        self,
        mock_tmpl_repo_cls,
        mock_probe_cls,
        mock_whisper_cls,
        client,
        stub_usage_ledger,
    ):
        """Record AFTER the call, never before: a call that failed cost nothing.

        Charging on attempt would let a run of Whisper outages burn the month's
        budget without a single transcription being produced.
        """
        from app.services.exceptions import WhisperUnavailableError

        mock_probe_cls.return_value.measure_seconds = AsyncMock(return_value=5.0)
        mock_tmpl_repo_cls.return_value.get_active_session = AsyncMock(
            return_value=MagicMock(id=uuid4(), language="es")
        )
        mock_whisper_cls.return_value.transcribe = AsyncMock(
            side_effect=WhisperUnavailableError()
        )

        response = client.post(
            "/api/transcriptions/transcribe",
            files={"file": ("a.webm", b"\x00\x01\x02", "audio/webm")},
        )

        assert response.status_code == 502
        assert stub_usage_ledger.recorded == [], "a failed call must not be charged"
