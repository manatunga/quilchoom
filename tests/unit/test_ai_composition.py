"""
Tests composition of Quilchoom's configured AI infrastructure.
"""

import pytest

import quilchoom.infrastructure.ai.composition as composition_module
from quilchoom.infrastructure.ai.composition import create_knowledge_interpreter
from quilchoom.infrastructure.ai.config import AIConfig
from quilchoom.infrastructure.ai.errors import AIConfigurationError


def test_rejects_unsupported_ai_provider(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = AIConfig(
        provider="grok",
        model="test-model",
    )

    with pytest.raises(
        AIConfigurationError,
        match="Unsupported AI provider",
    ):
        create_knowledge_interpreter(config)


def test_openai_composition_requires_credential(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = AIConfig(
        provider="openai",
        model="test-model",
    )

    with pytest.raises(
        AIConfigurationError,
        match="OPENAI_API_KEY",
    ):
        create_knowledge_interpreter(config)


def test_composes_openai_knowledge_interpreter(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    fake_openai_provider = object()
    fake_retrying_provider = object()
    fake_interpreter = object()

    captured_openai_kwargs: dict[str, object] = {}
    captured_retry_provider: list[object] = []
    captured_interpreter_provider: list[object] = []

    def fake_openai_provider_factory(**kwargs: object) -> object:
        captured_openai_kwargs.update(kwargs)
        return fake_openai_provider

    def fake_retrying_provider_factory(provider: object) -> object:
        captured_retry_provider.append(provider)
        return fake_retrying_provider

    def fake_interpreter_factory(provider: object) -> object:
        captured_interpreter_provider.append(provider)
        return fake_interpreter

    monkeypatch.setattr(
        composition_module,
        "OpenAIProvider",
        fake_openai_provider_factory,
    )
    monkeypatch.setattr(
        composition_module,
        "RetryingLLMProvider",
        fake_retrying_provider_factory,
    )
    monkeypatch.setattr(
        composition_module,
        "LLMKnowledgeInterpreter",
        fake_interpreter_factory,
    )

    config = AIConfig(
        provider=" OpenAI ",
        model="test-model",
        endpoint="https://example.test/v1",
    )

    result = create_knowledge_interpreter(config)

    assert result is fake_interpreter

    assert captured_openai_kwargs == {
        "model": "test-model",
        "api_key": "test-key",
        "endpoint": "https://example.test/v1",
    }
    assert captured_retry_provider == [fake_openai_provider]
    assert captured_interpreter_provider == [fake_retrying_provider]
