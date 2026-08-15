"""Shared test fixtures for backend tests."""

import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure the backend app package is importable in tests
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rate_limit import limiter  # noqa: E402  (needs the path insert above)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Give every test a clean rate-limit budget.

    The limiter keys on the client address, and every request from Starlette's
    ``TestClient`` reports the same one (``testclient``). Without this reset the
    counters accumulate **across tests**: the 11th request in the whole session
    would get a 429, and which test that lands on depends on collection order. The
    result is a suite that fails somewhere unrelated to the change that broke it.

    Resetting rather than disabling is deliberate — the limiter stays live, so the
    dedicated tests in ``test_rate_limit.py`` exercise the real thing instead of a
    stub that could drift from it.
    """
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def stub_usage_ledger():
    """Replace the spend ledger's DATABASE access, not the budget logic.

    The billable routes build ``UsageBudget(UsageRepository(pool))``. In tests the
    pool is a MagicMock, so the real repository would blow up on ``acquire()``.
    Patching the repository alone keeps ``UsageBudget`` — the ceilings, the day and
    month windows, the check/record ordering — **running for real** in every
    endpoint test, with an empty ledger. Stubbing the budget instead would leave the
    cost control untested precisely where it is wired in.

    Yields the stub so a test can pre-load spend (``stub_usage_ledger.spent = ...``)
    or assert what was charged (``stub_usage_ledger.recorded``).
    """
    from decimal import Decimal

    class _StubUsageRepository:
        spent = Decimal("0")
        recorded: list = []

        def __init__(self, pool=None):
            pass

        async def record(self, operation, estimated_cost_usd, session_id=None):
            _StubUsageRepository.recorded.append(
                (operation, estimated_cost_usd, session_id)
            )
            _StubUsageRepository.spent += estimated_cost_usd

        async def spent_since(self, instant):
            return _StubUsageRepository.spent

    # A fresh class per test, so `spent` and `recorded` cannot leak between them.
    _StubUsageRepository.recorded = []

    targets = [
        "app.routes.transcription_routes.UsageRepository",
        "app.routes.extraction_routes.UsageRepository",
        "app.routes.template_routes.UsageRepository",
    ]
    with ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, _StubUsageRepository))
        yield _StubUsageRepository
