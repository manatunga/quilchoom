"""
Unit tests on OpenAI LLM provider adapter.
"""

from types import SimpleNamespace
from typing import cast

import httpx2
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

import quilchoom.infrastructure.ai.openai_provider as openai_provider_module
from quilchoom.infrastructure.ai.errors import (
    AIAuthenticationError,
    AIConnectionError,
    AIProviderError,
    AIRateLimitError,
    AIResponseError,
)
from quilchoom.infrastructure.ai.openai_provider import (
    OpenAIProvider,
)
from quilchoom.interfaces.llm_provider import JSONSchema, LLMRequest


class FakeResponses:
    """Records OpenAI Responses API calls and returns or raises a configured result."""

    def __init__(
        self,
        response: object | None = None,
        error: Exception | None = None,
    ):
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        return self.response


class FakeOpenAIClient:
    """Provides a fake OpenAI client with a recording Responses API."""

    def __init__(
        self,
        response: object | None = None,
        error: Exception | None = None,
    ):
        self.responses = FakeResponses(
            response=response,
            error=error,
        )


def make_http_response(status_code: int) -> httpx2.Response:
    request = httpx2.Request(
        "POST",
        "https://api.openai.com/v1/responses",
    )
    return httpx2.Response(
        status_code=status_code,
        request=request,
    )


def test_request_and_schema_correctly_translated_and_returns_llm_response():
    response = SimpleNamespace(
        status="completed",
        output_text='{"candidates": []}',
        usage=None,
    )

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )

    fake_client = FakeOpenAIClient(response)
    provider._client = cast(OpenAI, fake_client)

    request = LLMRequest(
        instructions="Interpret this evidence.",
        input='{"project": {"name": "Quilchoom"}}',
    )
    schema: JSONSchema = {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "array",
            }
        },
    }

    result = provider.generate_structured(request, schema)

    assert result.output == {"candidates": []}
    assert result.usage is None

    assert len(fake_client.responses.calls) == 1

    call = fake_client.responses.calls[0]

    assert call["model"] == "test-model"
    assert call["instructions"] == request.instructions
    assert call["input"] == request.input
    assert call["text"] == {
        "format": {
            "type": "json_schema",
            "name": "quilchoom_response",
            "schema": schema,
            "strict": True,
        }
    }


def test_extracts_usage_from_openai_response():
    response = SimpleNamespace(
        status="completed",
        output_text='{"result": "success"}',
        usage=SimpleNamespace(
            input_tokens=12,
            output_tokens=7,
        ),
    )

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )
    fake_client = FakeOpenAIClient(response)
    provider._client = cast(OpenAI, fake_client)

    result = provider.generate_structured(
        LLMRequest(instructions="Test", input="{}"),
        {},
    )

    assert result.output == {"result": "success"}
    assert result.usage is not None
    assert result.usage.input_tokens == 12
    assert result.usage.output_tokens == 7


def test_rejects_malformed_structured_output():
    response = SimpleNamespace(
        status="completed",
        output_text="not valid json",
        usage=None,
    )

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )
    fake_client = FakeOpenAIClient(response)
    provider._client = cast(OpenAI, fake_client)

    with pytest.raises(AIResponseError):
        provider.generate_structured(
            LLMRequest(instructions="Test", input="{}"),
            {},
        )


def test_rejects_structured_output_that_is_not_object():
    response = SimpleNamespace(
        status="completed",
        output_text='["not", "an", "object"]',
        usage=None,
    )

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )
    fake_client = FakeOpenAIClient(response)
    provider._client = cast(OpenAI, fake_client)

    with pytest.raises(AIResponseError):
        provider.generate_structured(
            LLMRequest(instructions="Test", input="{}"),
            {},
        )


def test_translates_openai_connection_error():
    request = httpx2.Request(
        "POST",
        "https://api.openai.com/v1/responses",
    )
    openai_error = APIConnectionError(request=request)

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )
    fake_client = FakeOpenAIClient(error=openai_error)
    provider._client = cast(OpenAI, fake_client)

    with pytest.raises(AIConnectionError) as exc_info:
        provider.generate_structured(
            LLMRequest(instructions="Test", input="{}"),
            {},
        )

    assert exc_info.value.__cause__ is openai_error
    assert len(fake_client.responses.calls) == 1


def test_translates_openai_authentication_error():
    response = make_http_response(401)
    openai_error = AuthenticationError(
        "Invalid API key.",
        response=response,
        body=None,
    )

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )
    fake_client = FakeOpenAIClient(error=openai_error)
    provider._client = cast(OpenAI, fake_client)

    with pytest.raises(AIAuthenticationError) as exc_info:
        provider.generate_structured(
            LLMRequest(instructions="Test", input="{}"),
            {},
        )

    assert exc_info.value.__cause__ is openai_error
    assert len(fake_client.responses.calls) == 1


def test_translates_openai_rate_limit_error():
    response = make_http_response(429)
    openai_error = RateLimitError(
        "Rate limit exceeded.",
        response=response,
        body=None,
    )

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )
    fake_client = FakeOpenAIClient(error=openai_error)
    provider._client = cast(OpenAI, fake_client)

    with pytest.raises(AIRateLimitError) as exc_info:
        provider.generate_structured(
            LLMRequest(instructions="Test", input="{}"),
            {},
        )

    assert exc_info.value.__cause__ is openai_error
    assert len(fake_client.responses.calls) == 1


def test_translates_other_openai_status_error():
    response = make_http_response(500)
    openai_error = APIStatusError(
        "OpenAI request failed.",
        response=response,
        body=None,
    )

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )
    fake_client = FakeOpenAIClient(error=openai_error)
    provider._client = cast(OpenAI, fake_client)

    with pytest.raises(AIProviderError) as exc_info:
        provider.generate_structured(
            LLMRequest(instructions="Test", input="{}"),
            {},
        )

    assert exc_info.value.__cause__ is openai_error
    assert len(fake_client.responses.calls) == 1


def test_rejects_incomplete_openai_response():
    response = SimpleNamespace(
        status="incomplete",
        output_text='{"partial":',
        usage=None,
    )

    provider = OpenAIProvider(
        model="test-model",
        api_key="test-key",
    )
    fake_client = FakeOpenAIClient(response)
    provider._client = cast(OpenAI, fake_client)

    with pytest.raises(
        AIResponseError,
        match="incomplete structured response",
    ):
        provider.generate_structured(
            LLMRequest(instructions="Test", input="{}"),
            {},
        )


def test_configures_openai_client_sdk_retries(
    monkeypatch: pytest.MonkeyPatch,
):
    captured_kwargs: dict[str, object] = {}

    def fake_openai(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        return object()

    monkeypatch.setattr(
        openai_provider_module,
        "OpenAI",
        fake_openai,
    )

    OpenAIProvider(
        model="test-model",
        api_key="test-key",
        endpoint="https://example.test/v1",
    )

    assert captured_kwargs["api_key"] == "test-key"
    assert captured_kwargs["base_url"] == "https://example.test/v1"
    assert captured_kwargs["max_retries"] == 0
