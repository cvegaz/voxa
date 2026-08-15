"""Unit tests for AudioDurationProbe (ADR-0019 §1).

These tests never shell out: ``asyncio.create_subprocess_exec`` is patched, so the
suite keeps running on a machine without ``ffmpeg`` installed (ADR-0009 — the suite
is offline and must not depend on the environment).

The behavior under test is deliberately paranoid. Every failure mode of the probe
resolves to ``AudioUnreadableError`` and therefore to a rejected upload, because an
audio file we cannot measure is indistinguishable from one hiding an hour of
narration — and admitting it would reopen exactly the hole ADR-0019 closes.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audio_probe import AudioDurationProbe
from app.services.exceptions import AudioUnreadableError


def _fake_process(stdout: bytes = b"", returncode: int = 0) -> MagicMock:
    """A stand-in for the ffprobe subprocess."""
    process = MagicMock()
    process.returncode = returncode
    process.communicate = AsyncMock(return_value=(stdout, b""))
    process.kill = MagicMock()
    process.wait = AsyncMock()
    return process


class TestAudioDurationProbeSuccess:
    """A well-formed ffprobe reading is returned as seconds."""

    @pytest.mark.asyncio
    async def test_returns_measured_seconds(self):
        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_process(stdout=b"12.480000\n")),
        ):
            assert await probe.measure_seconds(b"audio bytes") == pytest.approx(12.48)

    @pytest.mark.asyncio
    async def test_handles_output_without_trailing_newline(self):
        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_process(stdout=b"3.5")),
        ):
            assert await probe.measure_seconds(b"audio bytes") == pytest.approx(3.5)


class TestAudioDurationProbeFailsClosed:
    """Every unreadable case must reject, never fall through to a default."""

    @pytest.mark.asyncio
    async def test_missing_ffprobe_binary_rejects(self):
        """A deployment without ffmpeg must fail loudly, not silently lose the cap."""
        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=FileNotFoundError()),
        ):
            with pytest.raises(AudioUnreadableError):
                await probe.measure_seconds(b"audio bytes")

    @pytest.mark.asyncio
    async def test_nonzero_exit_code_rejects(self):
        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_process(stdout=b"", returncode=1)),
        ):
            with pytest.raises(AudioUnreadableError):
                await probe.measure_seconds(b"not really audio")

    @pytest.mark.asyncio
    async def test_na_duration_rejects(self):
        """ffprobe prints 'N/A' for a progressively-written WebM with no duration.

        This is the exact case a pure-Python header parser would also hit, and the
        reason the cap cannot be enforced from container metadata alone.
        """
        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_process(stdout=b"N/A\n")),
        ):
            with pytest.raises(AudioUnreadableError):
                await probe.measure_seconds(b"audio bytes")

    @pytest.mark.asyncio
    async def test_empty_output_rejects(self):
        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_process(stdout=b"")),
        ):
            with pytest.raises(AudioUnreadableError):
                await probe.measure_seconds(b"audio bytes")

    @pytest.mark.asyncio
    async def test_zero_duration_rejects(self):
        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_process(stdout=b"0.000000\n")),
        ):
            with pytest.raises(AudioUnreadableError):
                await probe.measure_seconds(b"audio bytes")

    @pytest.mark.asyncio
    async def test_timeout_kills_the_process_and_rejects(self):
        """A crafted file must not be able to pin a worker indefinitely."""
        process = _fake_process()
        process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(return_value=process),
        ):
            with pytest.raises(AudioUnreadableError):
                await probe.measure_seconds(b"audio bytes")

        process.kill.assert_called_once()


class TestAudioDurationProbeTempFileHygiene:
    """The payload is written to a temp file; it must not survive the call."""

    @pytest.mark.asyncio
    async def test_temp_file_is_removed_after_success(self):
        captured: list[str] = []

        async def _capture(*args, **kwargs):
            captured.append(args[-1])  # the path is the last ffprobe argument
            return _fake_process(stdout=b"5.0\n")

        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=_capture),
        ):
            await probe.measure_seconds(b"audio bytes")

        import os

        assert captured, "ffprobe should have been invoked with a path"
        assert not os.path.exists(captured[0])

    @pytest.mark.asyncio
    async def test_temp_file_is_removed_after_failure(self):
        captured: list[str] = []

        async def _capture(*args, **kwargs):
            captured.append(args[-1])
            return _fake_process(stdout=b"N/A\n")

        probe = AudioDurationProbe()
        with patch(
            "app.services.audio_probe.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=_capture),
        ):
            with pytest.raises(AudioUnreadableError):
                await probe.measure_seconds(b"audio bytes")

        import os

        assert captured
        assert not os.path.exists(captured[0])
