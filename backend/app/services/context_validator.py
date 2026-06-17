"""Context validation service.

Validates the user-provided context string for the Excel template:
- Minimum length: 50 characters
- Maximum length: 3000 characters
"""

from app.models import ValidationResult


class ContextValidator:
    """Validates the user context string for length constraints."""

    MIN_LENGTH = 50
    MAX_LENGTH = 3000

    def validate(self, context: str) -> ValidationResult:
        """Validate the length of the context string.

        Args:
            context: The user-provided context describing the Excel template.

        Returns:
            ValidationResult with is_valid=True on success, or
            is_valid=False with error_code and detail on failure.
        """
        if len(context) < self.MIN_LENGTH:
            return ValidationResult(
                is_valid=False,
                error_code="CONTEXT_TOO_SHORT",
                detail=(
                    f"El contexto debe tener al menos {self.MIN_LENGTH} caracteres. "
                    f"Actualmente tiene {len(context)} caracteres."
                ),
            )

        if len(context) > self.MAX_LENGTH:
            return ValidationResult(
                is_valid=False,
                error_code="CONTEXT_TOO_LONG",
                detail=(
                    f"El contexto no debe exceder {self.MAX_LENGTH} caracteres. "
                    f"Actualmente tiene {len(context)} caracteres."
                ),
            )

        return ValidationResult(is_valid=True)
