"""
Defines the provider-neutral interface for structured LLM generation.
"""

from typing import Protocol

from pydantic import BaseModel, Field

type JSONSchema = dict[str, object]


class LLMRequest(BaseModel):
    """Represents a provider-neutral structured generation request."""

    instructions: str
    input: str


class LLMUsage(BaseModel):
    """Represents portable token usage reported by an LLM provider."""

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class LLMResponse(BaseModel):
    """Represents a successful structured response from an LLM provider."""

    output: dict[str, object]
    usage: LLMUsage | None = None


class LLMProvider(Protocol):
    """Defines the contract for provider-neutral structured LLM generation."""

    def generate_structured(
        self,
        request: LLMRequest,
        schema: JSONSchema,
    ) -> LLMResponse: ...
