"""Server-side measurement of an audio file's real duration (ADR-0019 §1).

Why this module exists
----------------------
ADR-0014 capped recordings at 20 s and explicitly rejected client-only enforcement
because "an upload (or a tampered client) bypasses it, and the server pays the
Whisper cost anyway". The implementation never realized that intent: the endpoint
received ``duration`` as a **form field** and validated that number, not the file.
The attack surface is the endpoint, not the browser — it accepts ``wav``/``mp4``/
``mpeg`` regardless of what the recorder produces, so a request claiming
``duration=5`` while carrying ten minutes of audio passed, and OpenAI billed the ten
minutes.

Why ffprobe and not a Python header parser
------------------------------------------
The obvious cheaper route — a pure-Python container parser — fails on the primary
format. ``mutagen`` does not support WebM at all, and Chrome's ``MediaRecorder``
writes WebM progressively while recording, so the duration element is commonly
absent or zero: it simply is not known when the header is written. Measuring
requires reading the stream, which is what ``ffprobe`` does.

Testability
-----------
The probe is injected through a constructor seam, the same pattern the OpenAI
services use (an optional client; ``None`` builds the real one). The test suite must
keep running on a machine without ``ffmpeg`` installed, so tests inject a stub and
never shell out.
"""

import asyncio
import os
import tempfile

from app.services.exceptions import AudioUnreadableError

# Bounded so a crafted file cannot hang a worker. ffprobe on a few MB is a
# sub-second operation; anything slower is pathological and we fail closed.
FFPROBE_TIMEOUT_SECONDS = 10.0


class AudioDurationProbe:
    """Measures the real duration of an audio payload with ``ffprobe``."""

    def __init__(self, ffprobe_path: str = "ffprobe"):
        self.ffprobe_path = ffprobe_path

    async def measure_seconds(self, data: bytes, suffix: str = "") -> float:
        """Return the audio's duration in seconds, measured from the bytes.

        Args:
            data: The raw uploaded audio.
            suffix: Optional filename suffix (e.g. ``.webm``). ffprobe detects the
                container from content, but a hint costs nothing and helps the
                occasional ambiguous stream.

        Raises:
            AudioUnreadableError: the file cannot be decoded, ffprobe is missing,
                the probe times out, or the reported duration is not a usable
                number. Every one of these fails CLOSED — see the exception's
                docstring for why admitting an unmeasurable file is not an option.
        """
        # ffprobe needs a seekable input to read container metadata reliably, so the
        # payload goes to a temp file rather than through a pipe. delete=False +
        # explicit unlink keeps this correct on every platform.
        handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            handle.write(data)
            handle.close()
            return await self._run_ffprobe(handle.name)
        finally:
            try:
                os.unlink(handle.name)
            except OSError:
                pass

    async def _run_ffprobe(self, path: str) -> float:
        try:
            process = await asyncio.create_subprocess_exec(
                self.ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except (FileNotFoundError, OSError) as exc:
            # ffprobe is not installed in this image. Loud, because a deployment
            # missing it would otherwise silently lose the cost control.
            raise AudioUnreadableError(
                "No se pudo verificar la duración del audio en el servidor."
            ) from exc

        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=FFPROBE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise AudioUnreadableError() from exc

        if process.returncode != 0:
            raise AudioUnreadableError()

        # ffprobe prints "N/A" when the container carries no usable duration — the
        # exact case of a progressively-written WebM. Not a number means not
        # measurable, and not measurable means rejected.
        raw = stdout.decode(errors="replace").strip()
        try:
            seconds = float(raw)
        except ValueError as exc:
            raise AudioUnreadableError() from exc

        if seconds <= 0:
            raise AudioUnreadableError()

        return seconds
