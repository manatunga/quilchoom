"""
Generates documentation from project knowledge using a structured LLM provider.
"""

from pydantic import ValidationError

from quilchoom.infrastructure.ai.errors import AIResponseError
from quilchoom.infrastructure.ai.models import (
    AIActiveClaimInput,
    AIDocumentGenerationInput,
    AIDocumentGenerationOutput,
    AIDocumentInput,
    AIProjectInput,
)
from quilchoom.interfaces.document_generator import (
    DocumentGenerationContext,
    DocumentGenerationResult,
)
from quilchoom.interfaces.llm_provider import LLMProvider, LLMRequest

GENERATION_INSTRUCTIONS = """
Generate a Markdown documentation artifact from the supplied project knowledge.

When generating the document:
- Use the document key and kind to determine the purpose and appropriate structure of the artifact.
- Use only the supplied knowledge claims as the factual basis for the document.
- Do not invent project facts, implementation details, developer intentions, motivations, decisions, causes, or outcomes that the supplied claims do not support.
- Write clear, useful documentation rather than merely listing or restating the supplied claims.
- Organize the Markdown appropriately for the document's purpose.
- Include only information relevant to the requested document.
- Return the IDs of only the supplied claims that actually support information included in the generated content.
- Do not return claim IDs for claims that were not used in the generated content.
- Do not reference or expose claim IDs in the Markdown content itself.

The generated content must be valid Markdown.
Return only data conforming to the requested structured output schema.
""".strip()


class LLMDocumentGenerator:
    """Generates documentation through a provider-neutral structured LLM interface."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate(
        self,
        context: DocumentGenerationContext,
    ) -> DocumentGenerationResult:
        ai_input = AIDocumentGenerationInput(
            project=AIProjectInput(
                name=context.project.name,
            ),
            document=AIDocumentInput(
                key=context.document.key,
                kind=context.document.kind,
            ),
            claims=[
                AIActiveClaimInput(
                    id=claim.id,
                    statement=claim.statement,
                    basis=claim.basis,
                    confidence=claim.confidence,
                )
                for claim in context.claims
            ],
        )

        request = LLMRequest(
            instructions=GENERATION_INSTRUCTIONS,
            input=ai_input.model_dump_json(),
        )

        response = self._provider.generate_structured(
            request=request,
            schema=AIDocumentGenerationOutput.model_json_schema(),
        )

        try:
            output = AIDocumentGenerationOutput.model_validate(response.output)
        except ValidationError as exc:
            raise AIResponseError(
                "LLM returned invalid structured document generation output."
            ) from exc

        return DocumentGenerationResult(
            content=output.content,
            claim_ids=output.claim_ids,
        )
