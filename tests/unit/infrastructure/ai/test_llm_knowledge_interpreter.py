"""
Tests LLM-backed knowledge interpretation behavior.
"""

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.history import HistoryEntry
from quilchoom.domain.interpretation import InterpretationContext
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.domain.project import Project
from quilchoom.infrastructure.ai.errors import AIResponseError
from quilchoom.infrastructure.ai.llm_knowledge_interpreter import (
    LLMKnowledgeInterpreter,
)
from quilchoom.infrastructure.ai.models import AIInterpretationOutput
from quilchoom.interfaces.llm_provider import (
    JSONSchema,
    LLMRequest,
    LLMResponse,
)


class RecordingLLMProvider:
    """Records structured generation calls for interpreter tests."""

    def generate_structured(
        self, request: LLMRequest, schema: JSONSchema
    ) -> LLMResponse:
        self.request = request
        self.schema = schema

        return LLMResponse(output={"candidates": []})


def test_interpreter_sends_only_deliberately_projected_context(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Create LLM Knowledge Interpreter",
        source="git",
        source_reference="a1b2c3d",
    )
    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git",
        reference="a1b2c3d",
        captured_at=datetime.now(UTC),
        source="git",
    )

    history_entry = HistoryEntry(
        event=event,
        evidence=evidence,
    )

    active_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Quilchoom captures Git commits.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    context = InterpretationContext(
        project=project,
        entries=[history_entry],
        active_claims=[active_claim],
    )

    provider = RecordingLLMProvider()
    interpreter = LLMKnowledgeInterpreter(provider)
    interpreter.interpret(context)

    input_data = json.loads(provider.request.input)

    assert input_data["project"]["name"] == "Quilchoom"
    assert "repository_path" not in input_data["project"]
    assert "id" not in input_data["project"]
    assert input_data["entries"][0]["evidence"]["id"] == str(evidence.id)

    event_data = input_data["entries"][0]["event"]
    evidence_data = input_data["entries"][0]["evidence"]
    claim_data = input_data["active_claims"][0]

    assert set(event_data) == {
        "type",
        "timestamp",
        "summary",
        "source",
        "source_reference",
    }

    assert set(evidence_data) == {
        "id",
        "type",
        "content",
        "reference",
        "source",
    }

    assert set(claim_data) == {
        "id",
        "statement",
        "basis",
        "confidence",
    }

    assert evidence_data["id"] == str(evidence.id)

    assert claim_data["id"] == str(active_claim.id)
    assert claim_data["statement"] == active_claim.statement
    assert claim_data["basis"] == ClaimBasis.OBSERVATION.value
    assert claim_data["confidence"] == ClaimConfidence.HIGH.value


def test_interpreter_passes_interpretation_output_schema_to_provider(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Create LLM Knowledge Interpreter",
        source="git",
        source_reference="a1b2c3d",
    )
    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git",
        reference="a1b2c3d",
        captured_at=datetime.now(UTC),
        source="git",
    )
    context = InterpretationContext(
        project=project,
        entries=[HistoryEntry(event=event, evidence=evidence)],
    )

    provider = RecordingLLMProvider()
    interpreter = LLMKnowledgeInterpreter(provider)

    interpreter.interpret(context)

    assert provider.schema == AIInterpretationOutput.model_json_schema()


def test_interpreter_maps_valid_ai_candidates_to_domain_candidates(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Create LLM Knowledge Interpreter",
        source="git",
        source_reference="a1b2c3d",
    )
    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git",
        reference="a1b2c3d",
        captured_at=datetime.now(UTC),
        source="git",
    )
    context = InterpretationContext(
        project=project,
        entries=[HistoryEntry(event=event, evidence=evidence)],
    )

    class CandidateProvider:
        def generate_structured(
            self,
            request: LLMRequest,
            schema: JSONSchema,
        ) -> LLMResponse:
            return LLMResponse(
                output={
                    "candidates": [
                        {
                            "statement": "Structured LLM interpretation was added.",
                            "basis": "observation",
                            "confidence": "high",
                            "evidence_ids": [str(evidence.id)],
                        }
                    ]
                }
            )

    interpreter = LLMKnowledgeInterpreter(CandidateProvider())

    result = interpreter.interpret(context)

    assert len(result.candidates) == 1

    candidate = result.candidates[0]
    assert candidate.statement == "Structured LLM interpretation was added."
    assert candidate.basis == ClaimBasis.OBSERVATION
    assert candidate.confidence == ClaimConfidence.HIGH
    assert candidate.evidence_ids == [evidence.id]


def test_interpreter_allows_zero_candidates(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Create LLM Knowledge Interpreter",
        source="git",
        source_reference="a1b2c3d",
    )
    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git",
        reference="a1b2c3d",
        captured_at=datetime.now(UTC),
        source="git",
    )
    context = InterpretationContext(
        project=project,
        entries=[HistoryEntry(event=event, evidence=evidence)],
    )

    provider = RecordingLLMProvider()
    interpreter = LLMKnowledgeInterpreter(provider)

    result = interpreter.interpret(context)

    assert result.candidates == []


def test_interpreter_translates_invalid_ai_output_to_response_error(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Create LLM Knowledge Interpreter",
        source="git",
        source_reference="a1b2c3d",
    )
    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git",
        reference="a1b2c3d",
        captured_at=datetime.now(UTC),
        source="git",
    )
    context = InterpretationContext(
        project=project,
        entries=[HistoryEntry(event=event, evidence=evidence)],
    )

    class InvalidOutputProvider:
        def generate_structured(
            self,
            request: LLMRequest,
            schema: JSONSchema,
        ) -> LLMResponse:
            return LLMResponse(
                output={
                    "candidates": [
                        {
                            "statement": "",
                            "basis": "guess",
                            "confidence": "certain",
                            "evidence_ids": [],
                        }
                    ]
                }
            )

    interpreter = LLMKnowledgeInterpreter(InvalidOutputProvider())

    with pytest.raises(AIResponseError) as exc_info:
        interpreter.interpret(context)

    assert isinstance(exc_info.value.__cause__, ValidationError)
