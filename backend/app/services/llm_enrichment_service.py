"""LLM Enrichment Service.

Sends user context and column schema to the OpenAI API to generate
an enriched context used for audio transcription data extraction.
"""

import asyncio
import os

import openai

from app.models import ColumnSchema
from app.services.exceptions import LLMInvalidResponseError, LLMUnavailableError


class LLMEnrichmentService:
    """Generates enriched context by calling OpenAI with user context + schema."""

    MAX_RETRIES = 2
    BACKOFF_DELAYS = [1, 3]  # seconds for retry 1 and retry 2
    MODEL = "gpt-4o-mini"

    def __init__(self, client: openai.AsyncOpenAI | None = None):
        """Initialize with an optional pre-configured OpenAI client.

        Args:
            client: An AsyncOpenAI client instance. If None, a new client
                    is created using the OPENAI_API_KEY env variable.
        """
        self._client = client or openai.AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
        )

    def _build_prompt(self, context: str, schema: ColumnSchema, language: str = "es") -> str:
        """Build the prompt combining user context and column schema.

        Args:
            context: The user-provided context describing the Excel template.
            schema: The column schema extracted from the Excel file.
            language: Language for the prompt and the enriched context ("es" or
                "en"). Defaults to Spanish.

        Returns:
            A formatted prompt string for the model.
        """
        if language == "en":
            columns_description = "\n".join(
                f"  - Column {col.index}: \"{col.name}\" "
                f"(Type: {col.data_type}, Example: \"{col.example_value}\")"
                for col in schema.columns
            )
            return (
                "You are an expert assistant in data processing and information "
                "extraction from audio transcriptions.\n\n"
                "The user has provided an Excel file as a data-capture template. "
                "Below is the file's context and its column schema.\n\n"
                "## User context\n\n"
                f"{context}\n\n"
                "## Column schema\n\n"
                f"{columns_description}\n\n"
                "## Instructions\n\n"
                "Based on the user context and the column schema, generate an enriched "
                "version of the context that will be used as a reference to extract "
                "structured data from audio transcriptions. The enriched context must:\n\n"
                "1. Clearly explain what kind of information is expected in each column.\n"
                "2. Describe natural-language patterns that could appear in an audio "
                "narration for each field.\n"
                "3. Include synonyms or variations of how a speaker might refer to each value.\n"
                "4. Be concise yet complete, focused on making automatic extraction easier.\n\n"
                "Respond only with the enriched context, with no additional explanations."
            )

        columns_description = "\n".join(
            f"  - Columna {col.index}: \"{col.name}\" "
            f"(Tipo: {col.data_type}, Ejemplo: \"{col.example_value}\")"
            for col in schema.columns
        )

        return (
            "Eres un asistente experto en procesamiento de datos y extracción de información "
            "desde transcripciones de audio.\n\n"
            "El usuario ha proporcionado un archivo Excel como plantilla de captura de datos. "
            "A continuación se describe el contexto del archivo y su esquema de columnas.\n\n"
            "## Contexto del usuario\n\n"
            f"{context}\n\n"
            "## Esquema de columnas\n\n"
            f"{columns_description}\n\n"
            "## Instrucciones\n\n"
            "Con base en el contexto del usuario y el esquema de columnas, genera una versión "
            "enriquecida del contexto que será usada como referencia para extraer datos "
            "estructurados de transcripciones de audio. El contexto enriquecido debe:\n\n"
            "1. Explicar claramente qué tipo de información se espera en cada columna.\n"
            "2. Describir patrones de lenguaje natural que podrían aparecer en una narración "
            "de audio para cada campo.\n"
            "3. Incluir sinónimos o variaciones de cómo un hablante podría referirse a cada dato.\n"
            "4. Ser conciso pero completo, enfocándose en facilitar la extracción automática.\n\n"
            "Responde únicamente con el contexto enriquecido, sin explicaciones adicionales."
        )

    def _is_transient_error(self, error: Exception) -> bool:
        """Determine if an error is transient and worth retrying.

        Transient errors include network issues, timeouts, and 5xx server errors.
        """
        if isinstance(error, (openai.APIConnectionError, openai.APITimeoutError)):
            return True
        if isinstance(error, openai.APIStatusError) and error.status_code >= 500:
            return True
        return False

    async def enrich(self, context: str, schema: ColumnSchema, language: str = "es") -> str:
        """Send context + schema to OpenAI and return the enriched context.

        Args:
            context: The user-provided context describing the Excel template.
            schema: The column schema extracted from the Excel file.
            language: Language for the enriched context ("es" or "en"). Defaults
                to Spanish.

        Returns:
            The enriched context string generated by the model.

        Raises:
            LLMUnavailableError: If OpenAI is unreachable after retries.
            LLMInvalidResponseError: If OpenAI returns an empty or invalid response.
        """
        prompt = self._build_prompt(context, schema, language)
        last_error: Exception | None = None

        for attempt in range(1 + self.MAX_RETRIES):
            try:
                completion = await self._client.chat.completions.create(
                    model=self.MODEL,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )

                # Extract text from response
                if not completion.choices:
                    raise LLMInvalidResponseError(
                        "La respuesta del LLM no contiene contenido."
                    )

                text = completion.choices[0].message.content

                if not text or not text.strip():
                    raise LLMInvalidResponseError(
                        "La respuesta del LLM es vacía o no contiene texto válido."
                    )

                return text

            except (LLMInvalidResponseError, LLMUnavailableError):
                # Don't retry our own custom errors for invalid responses
                raise

            except Exception as e:
                last_error = e

                if self._is_transient_error(e) and attempt < self.MAX_RETRIES:
                    delay = self.BACKOFF_DELAYS[attempt]
                    await asyncio.sleep(delay)
                    continue

                # Non-transient error or exhausted retries
                if self._is_transient_error(e):
                    raise LLMUnavailableError(
                        f"El servicio LLM no está disponible tras {self.MAX_RETRIES} reintentos. "
                        f"Error: {str(e)}"
                    ) from e

                # Non-transient API errors (e.g., 4xx auth errors)
                raise LLMUnavailableError(
                    f"Error al comunicarse con el servicio LLM: {str(e)}"
                ) from e

        # Should not reach here, but safety net
        raise LLMUnavailableError(
            f"El servicio LLM no está disponible tras {self.MAX_RETRIES} reintentos."
        ) from last_error
