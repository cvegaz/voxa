"""Tests for the coarse User-Agent buckets (ADR-0019 §7).

Order of checks is the whole difficulty here: every Chromium browser also claims
"Safari" in its UA string, and Edge and Opera also claim "Chrome". A parser that
checks in the wrong order reports plausible-looking nonsense — every Edge session
filed as Chrome — and nobody notices, because the numbers still add up.
"""

import pytest

from app.services.client_info import parse_browser, parse_platform, truncate

CHROME_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
SAFARI_IOS = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
CHROME_IOS = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) CriOS/126.0.0.0 Mobile/15E148 Safari/604.1"
)
EDGE_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like "
    "Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
)
FIREFOX_LINUX = "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0"
CHROME_ANDROID = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like "
    "Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
)


class TestBrowserBuckets:
    @pytest.mark.parametrize(
        "user_agent,expected",
        [
            (CHROME_MAC, "chrome"),
            (SAFARI_IOS, "safari"),
            (FIREFOX_LINUX, "firefox"),
            (CHROME_ANDROID, "chrome"),
        ],
    )
    def test_recognises_the_common_browsers(self, user_agent, expected):
        assert parse_browser(user_agent) == expected

    def test_edge_is_not_filed_as_chrome(self):
        """Edge's UA contains "Chrome" AND "Safari". Checking Chrome first would
        silently misfile every Edge session — plausible numbers, wrong story."""
        assert parse_browser(EDGE_WINDOWS) == "edge"

    def test_chrome_on_ios_is_its_own_bucket(self):
        """Worth separating: on iOS every browser is WebKit underneath, so a
        WebKit-specific capture problem shows up in Chrome-on-iOS too — and "just
        use Chrome" is not advice that helps an iPhone user."""
        assert parse_browser(CHROME_IOS) == "chrome-ios"

    def test_unknown_agents_are_bucketed_not_dropped(self):
        """A growing 'other' is itself the signal that the buckets need revisiting.
        Dropping them would hide exactly that."""
        assert parse_browser("SomeNewBrowser/1.0") == "other"

    def test_a_missing_header_is_none_not_other(self):
        """No header at all is a different fact from an unrecognised one."""
        assert parse_browser(None) is None
        assert parse_browser("") is None


class TestPlatformBuckets:
    @pytest.mark.parametrize(
        "user_agent,expected",
        [
            (CHROME_MAC, "macos"),
            (SAFARI_IOS, "ios"),
            (CHROME_IOS, "ios"),
            (EDGE_WINDOWS, "windows"),
            (FIREFOX_LINUX, "linux"),
            (CHROME_ANDROID, "android"),
        ],
    )
    def test_recognises_the_common_platforms(self, user_agent, expected):
        assert parse_platform(user_agent) == expected

    def test_android_is_not_filed_as_linux(self):
        """Android's UA says "Linux". Checking Linux first would erase the entire
        mobile picture — the population most likely to have capture problems."""
        assert parse_platform(CHROME_ANDROID) == "android"

    def test_a_missing_header_is_none(self):
        assert parse_platform(None) is None


class TestTruncate:
    def test_clamps_to_the_column_width(self):
        """A hostile header must not be able to break the INSERT."""
        assert len(truncate("x" * 500)) == 40

    def test_passes_none_through(self):
        assert truncate(None) is None
