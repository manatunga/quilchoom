"""
Tests retry behavior for transient LLM provider failures.
"""

import pytest

from quilchoom.infrastructure.ai.errors import (
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
)
from quilchoom.infrastructure.ai.retry import RetryingLLMProvider
from quilchoom.interfaces.llm_provider import JSONSchema, LLMRequest, LLMResponse


class FailsOnceProvider:
    """Fails once with a connection error before succeeding."""

    def __init__(self):
        self.attempts = 0

    def generate_structured(
        self, request: LLMRequest, schema: JSONSchema
    ) -> LLMResponse:
        self.attempts += 1

        if self.attempts == 1:
            raise AIConnectionError()

        return LLMResponse(output={"result": "success"})


class AlwaysFailsProvider:
    """Always fails with a configured AI error."""

    def __init__(self, error: Exception):
        self.error = error
        self.attempts = 0

    def generate_structured(
        self,
        request: LLMRequest,
        schema: JSONSchema,
    ) -> LLMResponse:
        self.attempts += 1
        raise self.error


def test_retries_connection_error_then_returns_success():
    inner_provider = FailsOnceProvider()

    sleep_delays: list[float] = []

    request = LLMRequest(
        instructions="Test instructions",
        input="{}",
    )
    schema: JSONSchema = {}

    provider = RetryingLLMProvider(
        inner_provider,
        sleep_fn=sleep_delays.append,
    )
    result = provider.generate_structured(request, schema)

    assert result.output == {"result": "success"}
    assert inner_provider.attempts == 2
    assert sleep_delays == [1.0]


def test_retries_rate_limit_error_then_returns_success():
    class RateLimitedOnceProvider:
        """Fails once with a rate-limit error before succeeding."""

        def __init__(self):
            self.attempts = 0

        def generate_structured(
            self,
            request: LLMRequest,
            schema: JSONSchema,
        ) -> LLMResponse:
            self.attempts += 1

            if self.attempts == 1:
                raise AIRateLimitError()

            return LLMResponse(output={"result": "success"})

    inner_provider = RateLimitedOnceProvider()
    sleep_delays: list[float] = []

    provider = RetryingLLMProvider(
        inner_provider,
        sleep_fn=sleep_delays.append,
    )

    result = provider.generate_structured(
        LLMRequest(instructions="Test instructions", input="{}"),
        {},
    )

    assert result.output == {"result": "success"}
    assert inner_provider.attempts == 2
    assert sleep_delays == [1.0]


def test_exhausts_retries_with_exponential_backoff():
    inner_provider = AlwaysFailsProvider(AIConnectionError())
    sleep_delays: list[float] = []

    provider = RetryingLLMProvider(
        inner_provider,
        sleep_fn=sleep_delays.append,
    )

    with pytest.raises(AIConnectionError):
        provider.generate_structured(
            LLMRequest(instructions="Test instructions", input="{}"),
            {},
        )

    assert inner_provider.attempts == 3
    assert sleep_delays == [1.0, 2.0]


def test_does_not_retry_non_transient_error():
    inner_provider = AlwaysFailsProvider(AIAuthenticationError())
    sleep_delays: list[float] = []

    provider = RetryingLLMProvider(
        inner_provider,
        sleep_fn=sleep_delays.append,
    )

    with pytest.raises(AIAuthenticationError):
        provider.generate_structured(
            LLMRequest(instructions="Test instructions", input="{}"),
            {},
        )

    assert inner_provider.attempts == 1
    assert sleep_delays == []


class RecordingFailsOnceProvider:
    """Records calls while failing once before succeeding."""

    def __init__(self):
        self.calls: list[tuple[LLMRequest, JSONSchema]] = []

    def generate_structured(
        self,
        request: LLMRequest,
        schema: JSONSchema,
    ) -> LLMResponse:
        self.calls.append((request, schema))

        if len(self.calls) == 1:
            raise AIConnectionError()

        return LLMResponse(output={"result": "success"})


def test_retry_reuses_same_request_and_schema():
    inner_provider = RecordingFailsOnceProvider()

    provider = RetryingLLMProvider(
        inner_provider,
        sleep_fn=lambda _: None,
    )

    request = LLMRequest(
        instructions="Test instructions",
        input='{"evidence": "test"}',
    )
    schema: JSONSchema = {
        "type": "object",
        "properties": {},
    }

    provider.generate_structured(request, schema)

    assert len(inner_provider.calls) == 2

    first_request, first_schema = inner_provider.calls[0]
    second_request, second_schema = inner_provider.calls[1]

    assert first_request is request
    assert second_request is request
    assert first_schema is schema
    assert second_schema is schema
