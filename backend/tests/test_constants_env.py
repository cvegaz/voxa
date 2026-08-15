"""The demo limits are configuration (ADR-0019 §4) — verify how they are read.

Two properties matter and neither is obvious from the values themselves:

1. **They are tunable from the environment**, so adapting the demo month to month
   is an ``.env`` edit and a restart rather than a rebuild and redeploy.
2. **A malformed value refuses to boot.** These are cost controls; a typo that
   silently falls back to a default is precisely the failure they exist to
   prevent, and it would only be discovered on the OpenAI bill. Failing at import
   surfaces it during the deploy instead.
"""

import importlib

import pytest

import app.constants as constants


def _reload_with(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(constants)


@pytest.fixture(autouse=True)
def _restore_constants():
    """Leave the module in its default state for every other test."""
    yield
    importlib.reload(constants)


class TestLimitsAreConfigurable:
    def test_max_duration_can_be_raised(self, monkeypatch):
        reloaded = _reload_with(monkeypatch, MAX_AUDIO_DURATION_SECONDS="45")
        assert reloaded.MAX_AUDIO_DURATION_SECONDS == 45.0

    def test_byte_ceiling_can_be_changed(self, monkeypatch):
        reloaded = _reload_with(monkeypatch, MAX_AUDIO_BYTES="1048576")
        assert reloaded.MAX_AUDIO_BYTES == 1048576

    def test_defaults_apply_when_unset(self, monkeypatch):
        monkeypatch.delenv("MAX_AUDIO_DURATION_SECONDS", raising=False)
        monkeypatch.delenv("MAX_AUDIO_BYTES", raising=False)
        reloaded = importlib.reload(constants)
        assert reloaded.MAX_AUDIO_DURATION_SECONDS == 20.0
        assert reloaded.MAX_AUDIO_BYTES == 4 * 1024 * 1024

    def test_the_anonymous_allowance_is_three_narrations(self, monkeypatch):
        """ADR-0019 §2. Lowered from 5; ONE constant serves this, not two.

        A second name (`ANONYMOUS_MAX_NARRATIONS` as its own constant) was
        rejected: with no accounts there is no second population to hold to a
        different number, and two constants where only one can apply eventually
        gets edited on the wrong side.
        """
        monkeypatch.delenv("ANONYMOUS_MAX_NARRATIONS", raising=False)
        assert importlib.reload(constants).MAX_ROWS_PER_SESSION == 3

    def test_the_allowance_is_configurable(self, monkeypatch):
        reloaded = _reload_with(monkeypatch, ANONYMOUS_MAX_NARRATIONS="10")
        assert reloaded.MAX_ROWS_PER_SESSION == 10

    def test_budget_ceilings_are_configurable(self, monkeypatch):
        reloaded = _reload_with(
            monkeypatch, DEMO_BUDGET_DAILY_USD="1.5", DEMO_BUDGET_MONTHLY_USD="25"
        )
        assert reloaded.DEMO_BUDGET_DAILY_USD == 1.5
        assert reloaded.DEMO_BUDGET_MONTHLY_USD == 25.0

    def test_blank_value_falls_back_to_the_default(self, monkeypatch):
        """An empty var in a .env file must not be read as zero."""
        reloaded = _reload_with(monkeypatch, MAX_AUDIO_DURATION_SECONDS="")
        assert reloaded.MAX_AUDIO_DURATION_SECONDS == 20.0


class TestMalformedLimitsFailFast:
    def test_non_numeric_duration_raises(self, monkeypatch):
        with pytest.raises(ValueError, match="MAX_AUDIO_DURATION_SECONDS"):
            _reload_with(monkeypatch, MAX_AUDIO_DURATION_SECONDS="veinte")

    def test_zero_duration_raises(self, monkeypatch):
        """Zero would disable capture entirely — never a plausible intent."""
        with pytest.raises(ValueError, match="positive"):
            _reload_with(monkeypatch, MAX_AUDIO_DURATION_SECONDS="0")

    def test_negative_byte_ceiling_raises(self, monkeypatch):
        with pytest.raises(ValueError, match="positive"):
            _reload_with(monkeypatch, MAX_AUDIO_BYTES="-1")

    def test_non_integer_byte_ceiling_raises(self, monkeypatch):
        with pytest.raises(ValueError, match="MAX_AUDIO_BYTES"):
            _reload_with(monkeypatch, MAX_AUDIO_BYTES="4.5")
