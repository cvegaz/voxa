"""ResponseParser service for parsing and validating Claude LLM JSON responses."""

import json

from app.models import ColumnSchema
from app.services.exceptions import LLMInvalidResponseError


class ResponseParser:
    """Parses and validates JSON responses from Claude against a ColumnSchema."""

    def parse(self, raw_response: str, schema: ColumnSchema) -> dict[str, str]:
        """
        Parsea la respuesta de Claude como JSON.
        Valida que las claves correspondan a las columnas del esquema.
        Asigna string vacío a campos faltantes o nulos.
        Retorna dict {column_name: value}.

        Args:
            raw_response: Raw JSON string response from Claude.
            schema: ColumnSchema defining expected columns.

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
                result[column.name] = str(value)

        return result
