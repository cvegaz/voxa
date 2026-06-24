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

    def test_duration_exactly_30_seconds_valid(self):
        file = _create_audio_upload()
        result = self.validator.validate(file, duration=30.0)
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
        result = self.validator.validate(file, duration=31.0)
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
        result = self.validator.validate(file, duration=30.01)
        assert result.is_valid is False
        assert result.error_code == "AUDIO_TOO_LONG"


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
