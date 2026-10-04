"""
Tests the integrated AI-backed knowledge interpretation pipeline.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import create_engine

from quilchoom.application.interpret_history import interpret_history
from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.history import DevelopmentHistory, HistoryEntry
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
)
from quilchoom.domain.project import Project
from quilchoom.infrastructure.ai.llm_knowledge_interpreter import (
    LLMKnowledgeInterpreter,
)
from quilchoom.infrastructure.ai.retry import RetryingLLMProvider
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    EvidenceRepository,
    InterpretationRunRepository,
    KnowledgeClaimRepository,
    ProjectRepository,
)
from quilchoom.interfaces.llm_provider import (
    JSONSchema,
    LLMRequest,
    LLMResponse,
)


class FakeLLMProvider:
    """Returns a configured structured response and records generation requests."""

    def __init__(self, response: LLMResponse):
        self.response = response
        self.requests: list[tuple[LLMRequest, JSONSchema]] = []

    def generate_structured(
        self,
        request: LLMRequest,
        schema: JSONSchema,
    ) -> LLMResponse:
        """Return the configured response and record the generation request."""

        self.requests.append((request, schema))
        return self.response


def test_ai_interpretation_pipeline_persists_generated_claim(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repo = ProjectRepository(db_engine)
    evidence_repo = EvidenceRepository(db_engine)
    claim_repo = KnowledgeClaimRepository(db_engine)
    run_repo = InterpretationRunRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Added authentication",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Add authentication",
        source="git",
        source_reference="commit-auth",
    )

    history = DevelopmentHistory(
        project_id=project.id,
        entries=[
            HistoryEntry(
                event=event,
                evidence=evidence,
            )
        ],
    )

    provider = FakeLLMProvider(
        LLMResponse(
            output={
                "candidates": [
                    {
                        "statement": "The project added authentication.",
                        "basis": "observation",
                        "confidence": "high",
                        "evidence_ids": [str(evidence.id)],
                    }
                ]
            }
        )
    )

    retrying_provider = RetryingLLMProvider(provider)
    interpreter = LLMKnowledgeInterpreter(retrying_provider)

    run = interpret_history(
        project=project,
        history=history,
        interpreter=interpreter,
        claim_repository=claim_repo,
        run_repository=run_repo,
    )

    assert len(provider.requests) == 1

    request, schema = provider.requests[0]
    input_data = json.loads(request.input)

    assert len(input_data["entries"]) == 1

    entry_data = input_data["entries"][0]
    evidence_data = entry_data["evidence"]

    assert evidence_data["id"] == str(evidence.id)
    assert evidence_data["type"] == "git_diff"
    assert evidence_data["content"] == "Added authentication"
    assert evidence_data["source"] == "git"

    assert schema["type"] == "object"

    properties = schema["properties"]

    assert isinstance(properties, dict)
    assert "candidates" in properties

    assert run is not None
    assert run.evidence_ids == [evidence.id]
    assert len(run.claim_ids) == 1

    persisted_claims = claim_repo.list_for_project(project.id)

    assert len(persisted_claims) == 1

    persisted_claim = persisted_claims[0]

    assert persisted_claim.id == run.claim_ids[0]
    assert persisted_claim.statement == "The project added authentication."
    assert persisted_claim.basis == ClaimBasis.OBSERVATION
    assert persisted_claim.confidence == ClaimConfidence.HIGH
    assert persisted_claim.status == ClaimStatus.ACTIVE
    assert persisted_claim.evidence_ids == [evidence.id]
