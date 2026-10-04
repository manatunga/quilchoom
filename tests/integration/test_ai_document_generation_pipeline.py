"""
Tests the integrated AI-backed document generation pipeline.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import create_engine

from quilchoom.application.generate_document import generate_document
from quilchoom.domain.document import DocumentVersionOrigin
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.domain.project import Project
from quilchoom.infrastructure.ai.llm_document_generator import (
    LLMDocumentGenerator,
)
from quilchoom.infrastructure.ai.retry import RetryingLLMProvider
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    EvidenceRepository,
    KnowledgeClaimRepository,
    ProjectRepository,
)
from quilchoom.interfaces.llm_provider import (
    JSONSchema,
    LLMRequest,
    LLMResponse,
)


class FakeLLMProvider:
    """Returns deterministic structured output for document generation tests."""

    def generate_structured(
        self,
        request: LLMRequest,
        schema: JSONSchema,
    ) -> LLMResponse:
        input_data = json.loads(request.input)

        claim_id = input_data["claims"][0]["id"]

        return LLMResponse(
            output={
                "content": (
                    "# Quilchoom\n\n"
                    "Quilchoom captures development activity as structured evidence."
                ),
                "claim_ids": [claim_id],
            }
        )


def test_ai_document_generation_pipeline_persists_generated_document(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repo = ProjectRepository(db_engine)
    evidence_repo = EvidenceRepository(db_engine)
    claim_repo = KnowledgeClaimRepository(db_engine)
    document_repo = DocumentRepository(db_engine)
    version_repo = DocumentVersionRepository(db_engine)

    project = Project(name="quilchoom", repository_path=tmp_path)
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Quilchoom captures development activity as structured evidence.",
        reference="test-reference",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Quilchoom captures development activity as structured evidence.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repo.save(claim)

    provider = RetryingLLMProvider(FakeLLMProvider())
    generator = LLMDocumentGenerator(provider)

    version = generate_document(
        project=project,
        key="readme",
        kind="readme",
        generator=generator,
        document_repository=document_repo,
        version_repository=version_repo,
        claim_repository=claim_repo,
    )

    document = document_repo.get_by_key(project.id, "readme")

    assert document is not None
    assert document.kind == "readme"
    assert version.document_id == document.id
    assert version.version_number == 1
    assert version.origin == DocumentVersionOrigin.GENERATED
    assert version.content == (
        "# Quilchoom\n\n"
        "Quilchoom captures development activity as structured evidence."
    )
    assert version.claim_ids == [claim.id]

    persisted_version = version_repo.get_latest(document.id)

    assert persisted_version is not None
    assert persisted_version.id == version.id
    assert persisted_version.document_id == document.id
    assert persisted_version.version_number == 1
    assert persisted_version.origin == DocumentVersionOrigin.GENERATED
    assert persisted_version.content == version.content
    assert persisted_version.claim_ids == [claim.id]
