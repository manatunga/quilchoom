"""
Implements structured LLM generation using OpenAI.
"""

import json

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from quilchoom.infrastructure.ai.errors import (
    AIAuthenticationError,
    AIConnectionError,
    AIProviderError,
    AIRateLimitError,
    AIResponseError,
)
from quilchoom.interfaces.llm_provider import (
    JSONSchema,
    LLMRequest,
    LLMResponse,
    LLMUsage,
)


class OpenAIProvider:
    """Provides structured LLM generation through OpenAI."""

    def __init__(self, model: str, api_key: str, endpoint: str | None = None):
        self._model = model
        self._client = OpenAI(
            api_key=api_key,
            base_url=endpoint,
            max_retries=0,
        )

    def generate_structured(
        self,
        request: LLMRequest,
        schema: JSONSchema,
    ) -> LLMResponse:
        """Generate structured output using OpenAI."""
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=request.instructions,
                input=request.input,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "quilchoom_response",
                        "schema": schema,
                        "strict": True,
                    }
                },
            )
        except APIConnectionError as exc:
            raise AIConnectionError("Could not connect to OpenAI.") from exc

        except AuthenticationError as exc:
            raise AIAuthenticationError(
                "OpenAI rejected the configured credentials."
            ) from exc

        except RateLimitError as exc:
            raise AIRateLimitError(
                "OpenAI temporarily rate-limited the request."
            ) from exc

        except APIStatusError as exc:
            raise AIProviderError("OpenAI request failed.") from exc

        if response.status == "incomplete":
            raise AIResponseError("OpenAI returned an incomplete structured response.")

        try:
            parsed_response = json.loads(response.output_text)
        except json.JSONDecodeError as exc:
            raise AIResponseError("OpenAI returned invalid structured output.") from exc

        if not isinstance(parsed_response, dict):
            raise AIResponseError("OpenAI structured output was not a JSON object.")

        if response.usage is not None:
            usage = LLMUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        else:
            usage = None

        return LLMResponse(
            output=parsed_response,
            usage=usage,
        )
