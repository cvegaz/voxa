"""Cross-layer constants for the capture/extraction flow (ADR-0013).

**Public-demo limits (ADR-0019) are read from the environment.** Voxa is exposed as
an anonymous demo whose caps are expected to move month to month as real usage
arrives, so tuning one must be an ``.env`` edit and a restart — never a rebuild and
redeploy. The defaults below are the safe values; the environment only widens or
tightens them.

Invalid values raise at import time **on purpose**: these are cost controls, and a
typo that silently falls back to a default is exactly the failure mode they exist to
prevent. Failing at boot surfaces the mistake during the deploy, not on the bill.
"""

import os


def _env_float(name: str, default: float) -> float:
    """Read a positive float from the environment, or fail loudly."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value


def _env_int(name: str, default: int) -> int:
    """Read a positive int from the environment, or fail loudly."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value


# A capture session is a short burst: the user narrates a handful of rows and
# downloads the result. After this many records the session auto-finalizes and
# accepts no more extractions.
#
# **This IS the anonymous trial allowance** (ADR-0019 §2, lowered from 5 to 3).
# The plan considered adding a second constant, ANONYMOUS_MAX_NARRATIONS, and it
# was rejected: Voxa has no accounts, so there is no second population to hold to
# a different number. Two constants where only one can ever apply is dead code
# that eventually gets edited on the wrong side. When accounts land, the free tier
# (10 entries, `todo.md` #11) becomes a per-plan lookup and *this* becomes the
# anonymous default — one value per population, still one meaning each.
#
# Reaching it is not an error: the session closes, the already-captured rows stay
# downloadable, and the UI offers to take an email.
MAX_ROWS_PER_SESSION = _env_int("ANONYMOUS_MAX_NARRATIONS", 3)

# Row of the first data record in the exported sheet. The export reconstructs the
# .xlsx from the schema with a single header row of column names on row 1, so the
# first data record lands on row 2.
FIRST_DATA_ROW = 2

# Allowed length of a single audio recording, in seconds.
#
# The 20 s cap comes from ADR-0014 and was RE-EXAMINED and KEPT by ADR-0019: at
# data-dictation pace one record with a date and a phone number takes 15-20 s to
# narrate, so a shorter cap would truncate legitimate narrations mid-sentence. What
# ADR-0019 changed is that the cap is now measured from the FILE (see
# ``AudioDurationProbe``) instead of a client-reported form field.
MIN_AUDIO_DURATION_SECONDS = _env_float("MIN_AUDIO_DURATION_SECONDS", 1.0)
MAX_AUDIO_DURATION_SECONDS = _env_float("MAX_AUDIO_DURATION_SECONDS", 20.0)

# Hard byte ceiling for an uploaded recording (ADR-0019 §1).
#
# This is NOT a duration control — size cannot bound duration when the client picks
# the bitrate (2 MB of Opus at 8 kbps is ~35 minutes of audio). It is a cheap
# pre-filter that stops us from reading an absurd upload into memory, writing it to
# a temp file, and handing it to ffprobe. The duration control is the probe.
#
# Sized to admit the most bloated format we accept: a 20 s WAV at 44.1 kHz/16-bit
# stereo is ~3.5 MB.
MAX_AUDIO_BYTES = _env_int("MAX_AUDIO_BYTES", 4 * 1024 * 1024)

# ── Public demo spend budget (ADR-0019 §3) ──────────────────────────────────
#
# Estimated unit costs per billable operation, in USD. These are ESTIMATES priced
# from OpenAI's published rates, not billed amounts: the ledger's job is to stop
# runaway spend, not to reconcile an invoice. They live in the environment so a
# price change is a config edit rather than a release.
#
# Derived from ~$0.006/min for Whisper and gpt-4o-mini's token rates, at the
# 20 s cap.
DEMO_COST_TRANSCRIPTION = _env_float("DEMO_COST_TRANSCRIPTION", 0.0020)
DEMO_COST_EXTRACTION = _env_float("DEMO_COST_EXTRACTION", 0.0004)
DEMO_COST_ENRICHMENT = _env_float("DEMO_COST_ENRICHMENT", 0.0005)

# Ceilings. The MONTHLY figure is the real stop; the DAILY one exists to bound
# the blast radius of a single bad night, because a monthly-only cap can be
# drained in one scripted afternoon and leave the demo dark for three weeks.
#
# The daily cap is deliberately ABOVE monthly/30 (~$0.23): sized at the average
# it would punish any good day. A saturated month therefore exhausts the monthly
# budget before day 30 — which is the intended behaviour, since running out is a
# demand signal that should trigger a config change, not a failure to prevent.
#
# The owner's hard ceiling is $10/month; $7 is the operating budget and the
# remaining $3 is headroom released BY HAND when the funnel data shows the wall
# is hitting real visitors.
DEMO_BUDGET_DAILY_USD = _env_float("DEMO_BUDGET_DAILY_USD", 0.45)
DEMO_BUDGET_MONTHLY_USD = _env_float("DEMO_BUDGET_MONTHLY_USD", 7.00)
