"""
Tests the document generation interface and data contracts.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.document import Document
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.domain.project import Project
from quilchoom.interfaces.document_generator import (
    DocumentGenerationContext,
    DocumentGenerationResult,
)


def make_claim(project_id):
    """Create a valid knowledge claim for document generation tests."""

    return KnowledgeClaim(
        project_id=project_id,
        statement="The project added authentication.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )


def test_document_generation_context_creation(tmp_path):
    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    claim = make_claim(project.id)

    context = DocumentGenerationContext(
        project=project,
        document=document,
        claims=[claim],
    )

    assert context.project == project
    assert context.document == document
    assert context.claims == [claim]


def test_document_generation_context_requires_claims(tmp_path):
    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )

    with pytest.raises(ValidationError):
        DocumentGenerationContext(
            project=project,
            document=document,
            claims=[],
        )


@pytest.mark.parametrize(
    "missing_field",
    ["project", "document", "claims"],
)
def test_document_generation_context_requires_fields(tmp_path, missing_field):
    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    claim = make_claim(project.id)

    data = {
        "project": project,
        "document": document,
        "claims": [claim],
    }
    del data[missing_field]

    with pytest.raises(ValidationError):
        DocumentGenerationContext(**data)


def test_document_generation_result_creation():
    claim_id = uuid4()

    result = DocumentGenerationResult(
        content="# Test Project",
        claim_ids=[claim_id],
    )

    assert result.content == "# Test Project"
    assert result.claim_ids == [claim_id]


def test_document_generation_result_rejects_empty_content():
    with pytest.raises(ValidationError):
        DocumentGenerationResult(
            content="",
            claim_ids=[uuid4()],
        )


def test_document_generation_result_requires_claim_provenance():
    with pytest.raises(ValidationError):
        DocumentGenerationResult(
            content="# Test Project",
            claim_ids=[],
        )
