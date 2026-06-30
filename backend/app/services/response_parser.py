"""ResponseParser service for parsing and validating the LLM's JSON responses."""

import json

from app.models import ColumnSchema
from app.services.date_normalizer import is_date_type, normalize_date_value
from app.services.exceptions import LLMInvalidResponseError


class ResponseParser:
    """Parses and validates the model's JSON responses against a ColumnSchema."""

    def parse(
        self, raw_response: str, schema: ColumnSchema, language: str = "es"
    ) -> dict[str, str]:
        """
        Parse the model's response as JSON.
        Validate that the keys correspond to the columns in the schema.
        Assign an empty string to missing or null fields.
        Normalize values of date-typed columns to the session language's date form.
        Return a dict {column_name: value}.

        Args:
            raw_response: Raw JSON string response from the model.
            schema: ColumnSchema defining expected columns.
            language: Session language ("es"/"en") for date formatting.

        Returns:
            Dictionary mapping column names to string values.

        Raises:
            LLMInvalidResponseError: If raw_response is not valid JSON.
        """
        try:
            parsed = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as e:
            raise LLMInvalidResponseError(
                detail=f"La respuesta del LLM no es JSON válido: {e}"
            )

        if not isinstance(parsed, dict):
            raise LLMInvalidResponseError(
                detail="La respuesta del LLM no es un objeto JSON válido."
            )

        result: dict[str, str] = {}
        for column in schema.columns:
            value = parsed.get(column.name)
            if value is None:
                result[column.name] = ""
            else:
                text = str(value)
                if is_date_type(column.data_type):
                    text = normalize_date_value(text, language)
                result[column.name] = text

        return result
