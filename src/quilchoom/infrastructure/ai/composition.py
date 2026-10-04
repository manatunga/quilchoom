"""
Composes Quilchoom's configured AI infrastructure.
"""

from quilchoom.infrastructure.ai.config import AIConfig
from quilchoom.infrastructure.ai.credentials import (
    resolve_environment_credential,
)
from quilchoom.infrastructure.ai.errors import AIConfigurationError
from quilchoom.infrastructure.ai.llm_knowledge_interpreter import (
    LLMKnowledgeInterpreter,
)
from quilchoom.infrastructure.ai.openai_provider import OpenAIProvider
from quilchoom.infrastructure.ai.retry import RetryingLLMProvider
from quilchoom.interfaces.knowledge_interpreter import KnowledgeInterpreter


def create_knowledge_interpreter(config: AIConfig) -> KnowledgeInterpreter:
    """Create a configured knowledge interpreter from AI configuration."""

    provider_name = config.provider.strip().lower()

    if provider_name != "openai":
        raise AIConfigurationError(f"Unsupported AI provider: '{config.provider}'.")

    credential = resolve_environment_credential("OPENAI_API_KEY")

    provider = OpenAIProvider(
        model=config.model,
        api_key=credential,
        endpoint=config.endpoint,
    )
    retrying_provider = RetryingLLMProvider(provider)

    return LLMKnowledgeInterpreter(retrying_provider)
