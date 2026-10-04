"""
Composes Quilchoom's configured AI infrastructure.
"""

from quilchoom.infrastructure.ai.config import AIConfig
from quilchoom.infrastructure.ai.credentials import (
    resolve_environment_credential,
)
from quilchoom.infrastructure.ai.errors import AIConfigurationError
from quilchoom.infrastructure.ai.llm_document_generator import LLMDocumentGenerator
from quilchoom.infrastructure.ai.llm_knowledge_interpreter import (
    LLMKnowledgeInterpreter,
)
from quilchoom.infrastructure.ai.openai_provider import OpenAIProvider
from quilchoom.infrastructure.ai.retry import RetryingLLMProvider
from quilchoom.interfaces.document_generator import DocumentGenerator
from quilchoom.interfaces.knowledge_interpreter import KnowledgeInterpreter
from quilchoom.interfaces.llm_provider import LLMProvider


def _create_llm_provider(config: AIConfig) -> LLMProvider:
    """Create a configured retrying LLM provider from AI configuration."""

    provider_name = config.provider.strip().lower()

    if provider_name != "openai":
        raise AIConfigurationError(f"Unsupported AI provider: '{config.provider}'.")

    credential = resolve_environment_credential("OPENAI_API_KEY")

    provider = OpenAIProvider(
        model=config.model,
        api_key=credential,
        endpoint=config.endpoint,
    )
    return RetryingLLMProvider(provider)


def create_knowledge_interpreter(config: AIConfig) -> KnowledgeInterpreter:
    """Create a configured knowledge interpreter from AI configuration."""

    provider = _create_llm_provider(config)

    return LLMKnowledgeInterpreter(provider)


def create_document_generator(config: AIConfig) -> DocumentGenerator:
    """Create a configured document generator from AI configuration."""

    provider = _create_llm_provider(config)

    return LLMDocumentGenerator(provider)
