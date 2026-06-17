"""LLM Extraction Service.

Sends a structured prompt to the Claude API to extract field values
from transcribed audio text based on the column schema.
"""

import asyncio
import os

import anthropic

from app.services.exceptions import LLMInvalidResponseError, LLMUnavailableError


class LLMExtractionService:
    """Extracts structured data from transcribed text by calling Claude."""

    MAX_RETRIES = 2
    RETRY_DELAYS = [1, 3]  # seconds for retry 1 and retry 2
    MODEL = "claude-sonnet-4-20250514"

    def __init__(self, client: anthropic.AsyncAnthropic | None = None):
        """Initialize with an optional pre-configured Anthropic client.

        Args:
            client: An AsyncAnthropic client instance. If None, a new client
                    is created using the ANTHROPIC_API_KEY env variable.
        """
        self._client = client or anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        )

    def _is_transient_error(self, error: Exception) -> bool:
        """Determine if an error is transient and worth retrying.

        Transient errors include network issues, timeouts, and 5xx server errors.
        """
        if isinstance(error, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
            return True
        if isinstance(error, anthropic.APIStatusError) and error.status_code >= 500:
            return True
        return False

    async def extract(self, prompt: str) -> str:
        """Send the prompt to Claude API and return the raw text response.

        Automatically retries on transient errors (timeout, 5xx, connection).

        Args:
            prompt: The fully constructed prompt string to send to Claude.

        Returns:
            The raw text content of Claude's response.

        Raises:
            LLMUnavailableError: If Claude is unreachable after retries.
            LLMInvalidResponseError: If Claude returns an empty response.
        """
        last_error: Exception | None = None

        for attempt in range(1 + self.MAX_RETRIES):
            try:
                message = await self._client.messages.create(
                    model=self.MODEL,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )

                # Extract text from response
                if not message.content:
                    raise LLMInvalidResponseError(
                        "La respuesta del LLM no contiene contenido."
                    )

                text_blocks = [
                    block.text
                    for block in message.content
                    if block.type == "text" and block.text.strip()
                ]

                if not text_blocks:
                    raise LLMInvalidResponseError(
                        "La respuesta del LLM es vacía o no contiene texto válido."
                    )

                return "\n".join(text_blocks)

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
