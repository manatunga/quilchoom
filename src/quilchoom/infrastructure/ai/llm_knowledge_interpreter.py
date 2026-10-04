"""
Implements knowledge interpretation using structured LLM generation.
"""

from pydantic import ValidationError

from quilchoom.domain.interpretation import (
    ClaimCandidate,
    InterpretationContext,
    InterpretationResult,
)
from quilchoom.infrastructure.ai.errors import AIResponseError
from quilchoom.infrastructure.ai.models import (
    AIActiveClaimInput,
    AIEventInput,
    AIEvidenceInput,
    AIHistoryEntryInput,
    AIInterpretationInput,
    AIInterpretationOutput,
    AIProjectInput,
)
from quilchoom.interfaces.llm_provider import LLMProvider, LLMRequest

INTERPRETATION_INSTRUCTIONS = """
Interpret the supplied development evidence into useful, traceable knowledge about the project.

For each claim candidate:
- Use "observation" when the statement is directly supported by the supplied evidence.
- Use "inference" when the statement is reasonably derived from the evidence but is not directly stated.
- Set confidence according to how strongly the supplied evidence supports the statement.
- Cite one or more evidence IDs from the supplied development entries that support the claim.
- Do not invent developer intentions, motivations, decisions, causes, or project facts that the evidence does not support.
- Treat existing active claims as context only, not as evidence for new claims.
- Avoid producing claims that merely duplicate existing active claims.

Prefer meaningful development knowledge over trivial restatements of individual evidence.
If the supplied evidence supports no useful new claims, return no candidates.
Return only data conforming to the requested structured output schema.
""".strip()


class LLMKnowledgeInterpreter:
    """Interprets Quilchoom development history using an LLM provider."""

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def _build_input(self, context: InterpretationContext) -> AIInterpretationInput:
        """Build AI-facing input from an interpretation context."""

        project = AIProjectInput(
            name=context.project.name,
        )

        entries: list[AIHistoryEntryInput] = []
        for entry in context.entries:
            event = AIEventInput(
                type=entry.event.type,
                timestamp=entry.event.timestamp,
                summary=entry.event.summary,
                source=entry.event.source,
                source_reference=entry.event.source_reference,
            )
            evidence = AIEvidenceInput(
                id=entry.evidence.id,
                type=entry.evidence.type,
                content=entry.evidence.content,
                reference=entry.evidence.reference,
                source=entry.evidence.source,
            )

            entries.append(
                AIHistoryEntryInput(
                    event=event,
                    evidence=evidence,
                )
            )

        active_claims: list[AIActiveClaimInput] = []
        for claim in context.active_claims:
            active_claim = AIActiveClaimInput(
                id=claim.id,
                statement=claim.statement,
                basis=claim.basis,
                confidence=claim.confidence,
            )

            active_claims.append(active_claim)

        return AIInterpretationInput(
            project=project,
            entries=entries,
            active_claims=active_claims,
        )

    def interpret(self, context: InterpretationContext) -> InterpretationResult:
        """Interpret development history into knowledge claim candidates."""

        ai_input = self._build_input(context)
        ai_input_json = ai_input.model_dump_json(indent=2)

        request = LLMRequest(
            instructions=INTERPRETATION_INSTRUCTIONS,
            input=ai_input_json,
        )

        json_schema = AIInterpretationOutput.model_json_schema()

        response = self._provider.generate_structured(
            request=request,
            schema=json_schema,
        )

        try:
            ai_output = AIInterpretationOutput.model_validate(response.output)
        except ValidationError as exc:
            raise AIResponseError(
                "AI provider returned invalid structured output."
            ) from exc

        candidates: list[ClaimCandidate] = []
        for candidate in ai_output.candidates:
            claim_candidate = ClaimCandidate(
                statement=candidate.statement,
                basis=candidate.basis,
                confidence=candidate.confidence,
                evidence_ids=candidate.evidence_ids,
            )
            candidates.append(claim_candidate)

        return InterpretationResult(candidates=candidates)
