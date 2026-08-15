"""Coarse browser/platform buckets parsed from the User-Agent (ADR-0019 §7).

Why this is not a contradiction of ADR-0019 §6
----------------------------------------------
§6 refuses to sniff the User-Agent, and the recorder does capability detection
instead. That refusal is about **control decisions** — deciding whether to let
someone record, based on a string the caller writes, is a rule the liar wins.

Here the same string feeds an **aggregate diagnostic**, and the trust calculus
inverts: if twenty Safari/iOS sessions die before the first narration, there is
something to fix, and one of them having lied does not change that conclusion.
Trust depends on what you do with a datum, not on the datum.

Deliberately coarse. A precise UA parser is a dependency with a table that rots
monthly, and the question being answered is "which platform is failing", not
"which patch version". Anything unrecognised is bucketed as ``other`` — never
dropped, because a growing ``other`` is itself the signal that the buckets need
revisiting.
"""

from typing import Optional

MAX_LENGTH = 40


def parse_browser(user_agent: Optional[str]) -> Optional[str]:
    """Return a coarse browser bucket, or None when there is nothing to read."""
    if not user_agent:
        return None
    ua = user_agent.lower()

    # Order matters: every Chromium browser also claims "safari", and Edge/Opera
    # also claim "chrome". Most specific first, always.
    if "edg/" in ua or "edge" in ua:
        return "edge"
    if "opr/" in ua or "opera" in ua:
        return "opera"
    if "firefox" in ua or "fxios" in ua:
        return "firefox"
    if "crios" in ua:
        # Chrome on iOS — still WebKit underneath, which is why "just use Chrome"
        # is not advice that helps an iPhone user.
        return "chrome-ios"
    if "chrome" in ua or "chromium" in ua:
        return "chrome"
    if "safari" in ua:
        return "safari"
    return "other"


def parse_platform(user_agent: Optional[str]) -> Optional[str]:
    """Return a coarse platform bucket, or None when there is nothing to read."""
    if not user_agent:
        return None
    ua = user_agent.lower()

    if "iphone" in ua or "ipad" in ua or "ipod" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    if "windows" in ua:
        return "windows"
    if "mac os" in ua or "macintosh" in ua:
        return "macos"
    if "linux" in ua:
        return "linux"
    return "other"


def truncate(value: Optional[str]) -> Optional[str]:
    """Clamp to the column width so a hostile header cannot break the insert."""
    if value is None:
        return None
    return value[:MAX_LENGTH]
