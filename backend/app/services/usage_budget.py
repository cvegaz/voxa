"""Hard USD ceilings for the anonymous public demo (ADR-0019 §3).

The per-IP rate limit (``app.rate_limit``) is the first layer: it stops one caller
from hammering the endpoints. It cannot stop a thousand honest visitors, nor one
caller rotating through a VPN, because both look like many different clients. This
module is the second layer — a **global** budget that does not care who is calling.

Two windows, on purpose:

* **Monthly** is the real stop, set from the owner's ceiling.
* **Daily** exists to bound the blast radius of a single bad night. A monthly-only
  cap can be drained in one scripted afternoon, leaving the demo dark for three
  weeks; a daily cap turns that catastrophe into a bad day that heals at midnight.

Exhausting the budget is a **success signal**, not a failure to prevent: it means
real demand arrived. The response invites the visitor to leave an email rather than
dead-ending them, and the owner widens the caps with a config edit.

On accuracy under concurrency
-----------------------------
The flow is *check → call OpenAI → record*, which leaves a classic TOCTOU window
(time-of-check to time-of-use): several requests in flight at once can each pass the
check before any of them records, overshooting the ceiling by up to the number of
concurrent requests. That is accepted deliberately. The overshoot is bounded by
in-flight concurrency on a single-process deployment — a handful of operations,
worth small fractions of a cent — and closing it would mean either a reservation
protocol with compensating writes on failure, or serialising every billable request
behind a lock. Neither is worth its complexity against a $10/month budget, and the
OpenAI account's own spending cap remains the true backstop.

Recording *after* the call is the other half of that trade: a failed OpenAI call
costs nothing, so it must not consume budget.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Optional
from uuid import UUID

from app.constants import (
    DEMO_BUDGET_DAILY_USD,
    DEMO_BUDGET_MONTHLY_USD,
    DEMO_COST_ENRICHMENT,
    DEMO_COST_EXTRACTION,
    DEMO_COST_TRANSCRIPTION,
)
from app.repositories import UsageRepository
from app.services.exceptions import DemoBudgetExhaustedError

# Operation names, also the values stored in usage_ledger.operation.
OPERATION_TRANSCRIPTION = "transcription"
OPERATION_EXTRACTION = "extraction"
OPERATION_ENRICHMENT = "enrichment"


def _unit_costs() -> dict[str, Decimal]:
    """Read the configured unit costs.

    Built per call rather than at import so tests (and a future hot-reload) can
    monkeypatch ``app.constants`` and be believed. Converted through ``str`` because
    ``Decimal(0.0004)`` from a float carries the float's binary error into what is
    supposed to be exact decimal arithmetic.
    """
    return {
        OPERATION_TRANSCRIPTION: Decimal(str(DEMO_COST_TRANSCRIPTION)),
        OPERATION_EXTRACTION: Decimal(str(DEMO_COST_EXTRACTION)),
        OPERATION_ENRICHMENT: Decimal(str(DEMO_COST_ENRICHMENT)),
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UsageBudget:
    """Guards billable operations against the daily and monthly USD ceilings."""

    def __init__(
        self,
        repository: UsageRepository,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        """
        Args:
            repository: ledger access.
            clock: injected so tests can cross a day or month boundary without
                waiting for one. Defaults to UTC now — UTC and not local time, so
                the window does not shift twice a year with daylight saving.
        """
        self._repository = repository
        self._clock = clock or _utc_now

    async def check(self) -> None:
        """Raise if either ceiling is already reached.

        Called BEFORE spending. Raising here means the request never reaches OpenAI,
        so a blocked request costs nothing.
        """
        now = self._clock()

        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if await self._repository.spent_since(day_start) >= Decimal(
            str(DEMO_BUDGET_DAILY_USD)
        ):
            raise DemoBudgetExhaustedError(
                "La demostración gratuita alcanzó su cupo de hoy. "
                "Déjanos tu correo y te damos acceso."
            )

        month_start = day_start.replace(day=1)
        if await self._repository.spent_since(month_start) >= Decimal(
            str(DEMO_BUDGET_MONTHLY_USD)
        ):
            raise DemoBudgetExhaustedError(
                "La demostración gratuita alcanzó su cupo del mes. "
                "Déjanos tu correo y te damos acceso."
            )

    async def record(self, operation: str, session_id: Optional[UUID] = None) -> None:
        """Charge one operation to the ledger. Called AFTER the call succeeds."""
        costs = _unit_costs()
        if operation not in costs:
            raise ValueError(f"Unknown billable operation: {operation!r}")

        await self._repository.record(
            operation=operation,
            estimated_cost_usd=costs[operation],
            session_id=session_id,
        )
