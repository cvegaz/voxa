"""Unit tests for AudioValidator service."""

import io
from unittest.mock import MagicMock

import pytest

from app.services.audio_validator import AudioValidator


def _create_audio_upload(
    content: bytes = b"fake audio data",
    content_type: str = "audio/webm",
    filename: str = "recording.webm",
) -> MagicMock:
    """Helper to create a mock UploadFile for audio testing."""
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.content_type = content_type
    mock_file.file = io.BytesIO(content)
    return mock_file


class TestAudioValidatorMimeType:
    """Tests for MIME type validation."""

    def setup_method(self):
        self.validator = AudioValidator()

    def test_valid_webm_mime_type(self):
        file = _create_audio_upload(content_type="audio/webm")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is True

    def test_valid_ogg_mime_type(self):
        file = _create_audio_upload(content_type="audio/ogg")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is True

    def test_valid_mp4_mime_type(self):
        file = _create_audio_upload(content_type="audio/mp4")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is True

    def test_valid_mpeg_mime_type(self):
        file = _create_audio_upload(content_type="audio/mpeg")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is True

    def test_valid_wav_mime_type(self):
        file = _create_audio_upload(content_type="audio/wav")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is True

    def test_valid_webm_with_codecs_parameter(self):
        """Browsers send 'audio/webm;codecs=opus'; the codec parameter must be ignored."""
        file = _create_audio_upload(content_type="audio/webm;codecs=opus")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is True

    def test_valid_ogg_with_codecs_parameter(self):
        """The codec parameter must be ignored for ogg too."""
        file = _create_audio_upload(content_type="audio/ogg; codecs=opus")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is True

    def test_invalid_text_mime_type(self):
        file = _create_audio_upload(content_type="text/plain")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is False
        assert result.error_code == "UNSUPPORTED_AUDIO_FORMAT"

    def test_invalid_video_mime_type(self):
        file = _create_audio_upload(content_type="video/mp4")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is False
        assert result.error_code == "UNSUPPORTED_AUDIO_FORMAT"

    def test_invalid_application_mime_type(self):
        file = _create_audio_upload(content_type="application/octet-stream")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is False
        assert result.error_code == "UNSUPPORTED_AUDIO_FORMAT"

    def test_none_mime_type(self):
        file = _create_audio_upload(content_type="audio/webm")
        file.content_type = None
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is False
        assert result.error_code == "UNSUPPORTED_AUDIO_FORMAT"


class TestAudioValidatorDuration:
    """Tests for duration validation."""

    def setup_method(self):
        self.validator = AudioValidator()

    def test_duration_exactly_1_second_valid(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=1.0)
        assert result.is_valid is True

    def test_duration_exactly_20_seconds_valid(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=20.0)
        assert result.is_valid is True

    def test_duration_15_seconds_valid(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=15.0)
        assert result.is_valid is True

    def test_duration_below_minimum_rejected(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=0.5)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_SHORT"

    def test_duration_zero_rejected(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=0.0)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_SHORT"

    def test_duration_above_maximum_rejected(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=21.0)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_LONG"

    def test_duration_very_long_rejected(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=120.0)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_LONG"

    def test_duration_just_below_minimum_rejected(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=0.99)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_SHORT"

    def test_duration_just_above_maximum_rejected(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=20.01)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_LONG"


class TestAudioValidatorConfigurableLimit:
    """The max duration is configurable for a future paid tier."""

    def test_default_validator_rejects_above_free_tier_cap(self):
        validator = AudioValidator()
        file = _create_audio_upload()
        result = validator.validate(file, duration=45.0)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_LONG"

    def test_custom_max_duration_allows_longer_recording(self):
        validator = AudioValidator(max_duration_seconds=60.0)
        file = _create_audio_upload()
        result = validator.validate(file, duration=45.0)
        assert result.is_valid is True


class TestAudioValidatorEmptyFile:
    """Tests for empty file validation."""

    def setup_method(self):
        self.validator = AudioValidator()

    def test_empty_file_rejected(self):
        file = _create_audio_upload(content=b"")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is False
        assert result.error_code == "EMPTY_AUDIO_FILE"

    def test_non_empty_file_passes(self):
        file = _create_audio_upload(content=b"some audio bytes")
        result = self.validator.validate(file, duration=5.0)
        assert result.is_valid is True


class TestAudioValidatorByteCeiling:
    """The byte cap (ADR-0019 §1).

    It is explicitly NOT a duration control — size cannot bound seconds when the
    client picks the bitrate. Its job is to stop an absurd upload from being
    buffered, written to a temp file and handed to a subprocess.
    """

    def test_file_within_ceiling_passes(self):
        validator = AudioValidator(max_bytes=1024)
        file = _create_audio_upload(content=b"x" * 1024)
        assert validator.validate(file, duration=5.0).is_valid is True

    def test_file_above_ceiling_rejected(self):
        validator = AudioValidator(max_bytes=1024)
        file = _create_audio_upload(content=b"x" * 1025)
        result = validator.validate(file, duration=5.0)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_LARGE"

    def test_size_is_checked_before_mime_type(self):
        """An oversized upload is rejected on size, whatever it claims to be."""
        validator = AudioValidator(max_bytes=10)
        file = _create_audio_upload(content=b"x" * 100, content_type="text/plain")
        assert validator.validate(file, duration=5.0).error_code == "AUDIO_TOO_LARGE"

    def test_empty_file_still_takes_priority_over_size(self):
        validator = AudioValidator(max_bytes=10)
        file = _create_audio_upload(content=b"")
        assert validator.validate(file, duration=5.0).error_code == "EMPTY_AUDIO_FILE"


class TestAudioValidatorValidateUpload:
    """``validate_upload`` runs only the checks that need no decoding.

    The route calls it before measuring the audio, so an already-invalid file never
    reaches the probe. It must therefore be complete on its own axes and say nothing
    about duration.
    """

    def setup_method(self):
        self.validator = AudioValidator(max_bytes=1024)

    def test_accepts_a_valid_upload_without_any_duration(self):
        file = _create_audio_upload()
        assert self.validator.validate_upload(file).is_valid is True

    def test_rejects_empty(self):
        file = _create_audio_upload(content=b"")
        assert self.validator.validate_upload(file).error_code == "EMPTY_AUDIO_FILE"

    def test_rejects_oversized(self):
        file = _create_audio_upload(content=b"x" * 2048)
        assert self.validator.validate_upload(file).error_code == "AUDIO_TOO_LARGE"

    def test_rejects_unsupported_mime(self):
        file = _create_audio_upload(content_type="text/plain")
        assert (
            self.validator.validate_upload(file).error_code
            == "UNSUPPORTED_AUDIO_FORMAT"
        )

    def test_leaves_the_stream_rewound_for_the_next_reader(self):
        """The route reads the bytes right after this call; position must be 0."""
        file = _create_audio_upload(content=b"some audio bytes")
        self.validator.validate_upload(file)
        assert file.file.tell() == 0


class TestAudioValidatorFailFast:
    """Tests for fail-fast behavior and error priority."""

    def setup_method(self):
        self.validator = AudioValidator()

    def test_empty_file_takes_priority_over_mime_type(self):
        """Empty file should be rejected before checking MIME type."""
        file = _create_audio_upload(content=b"", content_type="text/plain")
        result = self.validator.validate(file, duration=5.0)
        assert result.error_code == "EMPTY_AUDIO_FILE"

    def test_mime_type_takes_priority_over_duration(self):
        """MIME type should be checked before duration."""
        file = _create_audio_upload(content_type="video/mp4")
        result = self.validator.validate(file, duration=0.5)
        assert result.error_code == "UNSUPPORTED_AUDIO_FORMAT"

    def test_valid_file_returns_no_error_details(self):
        """A valid file should have no error_code or detail."""
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=10.0)
        assert result.is_valid is True
        assert result.error_code is None
        assert result.detail is None
