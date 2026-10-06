"""
Unit tests for validation boundaries of AI-facing data models.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.knowledge_claim import ClaimBasis, ClaimConfidence
from quilchoom.infrastructure.ai.models import (
    AIClaimCandidate,
    AIInterpretationInput,
    AIInterpretationOutput,
    AIProjectInput,
)


def test_ai_project_input_rejects_extra_fields(tmp_path):
    with pytest.raises(ValidationError):
        AIProjectInput(
            name="Quilchoom",
            repository_path=tmp_path,  # type: ignore
        )


def test_ai_interpretation_input_requires_at_least_one_entry():
    with pytest.raises(ValidationError):
        AIInterpretationInput(
            project=AIProjectInput(name="Quilchoom"),
            entries=[],
        )


def test_ai_claim_candidate_requires_non_empty_statement():
    with pytest.raises(ValidationError):
        AIClaimCandidate(
            statement="",
            basis=ClaimBasis.OBSERVATION,
            confidence=ClaimConfidence.HIGH,
            evidence_ids=[uuid4()],
        )


def test_ai_claim_candidate_requires_at_least_one_evidence_id():
    with pytest.raises(ValidationError):
        AIClaimCandidate(
            statement="A repository change was observed.",
            basis=ClaimBasis.OBSERVATION,
            confidence=ClaimConfidence.HIGH,
            evidence_ids=[],
        )


def test_ai_claim_candidate_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AIClaimCandidate(
            statement="A repository change was observed.",
            basis=ClaimBasis.OBSERVATION,
            confidence=ClaimConfidence.HIGH,
            evidence_ids=[uuid4()],
            reasoning="The model's internal explanation.",  # type: ignore
        )


def test_ai_interpretation_output_allows_zero_candidates():
    output = AIInterpretationOutput(candidates=[])

    assert output.candidates == []


def test_ai_interpretation_output_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AIInterpretationOutput(
            candidates=[],
            provider_metadata={"model": "example"},  # type: ignore
        )


def test_interpretation_output_schema_requires_candidates() -> None:
    schema = AIInterpretationOutput.model_json_schema()

    assert "candidates" in schema["required"]
