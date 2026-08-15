"""LLM Extraction Service.

Sends a structured prompt to the OpenAI API to extract field values
from transcribed audio text based on the column schema.
"""

import asyncio
import os

import openai

from app.services.exceptions import LLMInvalidResponseError, LLMUnavailableError


class LLMExtractionService:
    """Extracts structured data from transcribed text by calling OpenAI."""

    MAX_RETRIES = 2
    RETRY_DELAYS = [1, 3]  # seconds for retry 1 and retry 2
    MODEL = "gpt-4o-mini"

    def __init__(self, client: openai.AsyncOpenAI | None = None):
        """Initialize with an optional pre-configured OpenAI client.

        Args:
            client: An AsyncOpenAI client instance. If None, one is created
                    **lazily** on first use from the OPENAI_API_KEY env variable.

        The laziness matters. ``openai>=2`` raises ``OpenAIError: Missing
        credentials`` from the client CONSTRUCTOR, so building the client eagerly
        made merely *instantiating* this service require a key — even when no call
        would ever be made. The routes construct their services up front, so a test
        that mocked the orchestrator still exploded, and CI (which sets no
        environment variables) failed while every developer machine with a key
        exported passed. That violates the offline-suite guarantee of ADR-0009.

        Deferring construction to the first call means a missing key fails where it
        is actually a problem — at the moment of the API call — with the same error,
        and never where it is not.
        """
        self._explicit_client = client
        self._lazy_client: openai.AsyncOpenAI | None = None

    @property
    def _client(self) -> openai.AsyncOpenAI:
        """The injected client, or one built on first use."""
        if self._explicit_client is not None:
            return self._explicit_client
        if self._lazy_client is None:
            self._lazy_client = openai.AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY", ""),
            )
        return self._lazy_client

    def _is_transient_error(self, error: Exception) -> bool:
        """Determine if an error is transient and worth retrying.

        Transient errors include network issues, timeouts, and 5xx server errors.
        """
        if isinstance(error, (openai.APIConnectionError, openai.APITimeoutError)):
            return True
        if isinstance(error, openai.APIStatusError) and error.status_code >= 500:
            return True
        return False

    async def extract(self, prompt: str) -> str:
        """Send the prompt to OpenAI API and return the raw text response.

        Automatically retries on transient errors (timeout, 5xx, connection).

        Args:
            prompt: The fully constructed prompt string to send to the model.

        Returns:
            The raw text content of the model's response.

        Raises:
            LLMUnavailableError: If OpenAI is unreachable after retries.
            LLMInvalidResponseError: If OpenAI returns an empty response.
        """
        last_error: Exception | None = None

        for attempt in range(1 + self.MAX_RETRIES):
            try:
                completion = await self._client.chat.completions.create(
                    model=self.MODEL,
                    max_tokens=1024,
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
                # Don't retry our own custom errors
                raise

            except Exception as e:
                last_error = e

                if self._is_transient_error(e) and attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAYS[attempt]
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

        # Safety net - should not reach here
        raise LLMUnavailableError(
            f"El servicio LLM no está disponible tras {self.MAX_RETRIES} reintentos."
        ) from last_error
