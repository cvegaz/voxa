"""Unit tests for ContextValidator service."""

from app.services.context_validator import ContextValidator


class TestContextValidator:
    """Tests for ContextValidator.validate()."""

    def setup_method(self):
        self.validator = ContextValidator()

    # --- Valid contexts ---

    def test_valid_context_minimum_length(self):
        """Context with exactly 50 characters is accepted."""
        context = "a" * 50
        result = self.validator.validate(context)
        assert result.is_valid is True
        assert result.error_code is None
        assert result.detail is None

    def test_valid_context_maximum_length(self):
        """Context with exactly 3000 characters is accepted."""
        context = "b" * 3000
        result = self.validator.validate(context)
        assert result.is_valid is True
        assert result.error_code is None
        assert result.detail is None

    def test_valid_context_typical_length(self):
        """Context with a typical length (e.g., 200 characters) is accepted."""
        context = "Este es un contexto descriptivo para la plantilla Excel. " * 4
        # Ensure it's within range
        assert 50 <= len(context) <= 3000
        result = self.validator.validate(context)
        assert result.is_valid is True

    # --- Too short ---

    def test_context_too_short_49_chars(self):
        """Context with 49 characters is rejected as too short."""
        context = "a" * 49
        result = self.validator.validate(context)
        assert result.is_valid is False
        assert result.error_code == "CONTEXT_TOO_SHORT"
        assert "50" in result.detail
        assert "49" in result.detail

    def test_context_too_short_empty(self):
        """Empty context is rejected as too short."""
        context = ""
        result = self.validator.validate(context)
        assert result.is_valid is False
        assert result.error_code == "CONTEXT_TOO_SHORT"

    def test_context_too_short_one_char(self):
        """Single character context is rejected as too short."""
        context = "x"
        result = self.validator.validate(context)
        assert result.is_valid is False
        assert result.error_code == "CONTEXT_TOO_SHORT"

    # --- Too long ---

    def test_context_too_long_3001_chars(self):
        """Context with 3001 characters is rejected as too long."""
        context = "c" * 3001
        result = self.validator.validate(context)
        assert result.is_valid is False
        assert result.error_code == "CONTEXT_TOO_LONG"
        assert "3000" in result.detail
        assert "3001" in result.detail

    def test_context_too_long_large(self):
        """Very long context is rejected as too long."""
        context = "d" * 10000
        result = self.validator.validate(context)
        assert result.is_valid is False
        assert result.error_code == "CONTEXT_TOO_LONG"

    # --- Detail messages ---

    def test_short_context_detail_in_spanish(self):
        """Error detail for short context is in Spanish."""
        context = "corto"
        result = self.validator.validate(context)
        assert "caracteres" in result.detail

    def test_long_context_detail_in_spanish(self):
        """Error detail for long context is in Spanish."""
        context = "x" * 3001
        result = self.validator.validate(context)
        assert "caracteres" in result.detail
