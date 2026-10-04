"""
Provides retry behavior for transient LLM provider failures.
"""

from collections.abc import Callable
from time import sleep

from quilchoom.infrastructure.ai.errors import AIConnectionError, AIRateLimitError
from quilchoom.interfaces.llm_provider import (
    JSONSchema,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)

MAX_ATTEMPTS = 3
INITIAL_BACKOFF_SECONDS = 1.0


class RetryingLLMProvider:
    """Retries structured LLM generation after transient provider failures."""

    def __init__(
        self, provider: LLMProvider, *, sleep_fn: Callable[[float], None] = sleep
    ):
        self._provider = provider
        self._sleep = sleep_fn

    def generate_structured(
        self,
        request: LLMRequest,
        schema: JSONSchema,
    ) -> LLMResponse:
        """Generate structured output with retries for transient failures."""

        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self._provider.generate_structured(request, schema)
                return response

            except AIConnectionError, AIRateLimitError:
                if attempt == MAX_ATTEMPTS - 1:
                    raise

                delay = INITIAL_BACKOFF_SECONDS * (2**attempt)
                self._sleep(delay)

        raise RuntimeError("Retry loop completed without returning or raising.")
