"""
Tests the document generation application workflow.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from quilchoom.application.errors import (
    InvalidGeneratedClaimError,
    NoActiveClaimsError,
)
from quilchoom.application.generate_document import generate_document
from quilchoom.domain.document import Document, DocumentVersionOrigin
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    EvidenceRepository,
    KnowledgeClaimRepository,
    ProjectRepository,
)
from quilchoom.interfaces.document_generator import (
    DocumentGenerationContext,
    DocumentGenerationResult,
)


class RecordingDocumentGenerator:
    """Records the document generation context supplied by the application."""

    def __init__(self, result: DocumentGenerationResult) -> None:
        self.result = result
        self.received_context: DocumentGenerationContext | None = None

    def generate(
        self,
        context: DocumentGenerationContext,
    ) -> DocumentGenerationResult:
        self.received_context = context
        return self.result


class StubDocumentGenerator:
    """Returns a predetermined document generation result."""

    def __init__(self, result: DocumentGenerationResult) -> None:
        self.result = result
        self.call_count = 0

    def generate(
        self,
        context: DocumentGenerationContext,
    ) -> DocumentGenerationResult:
        self.call_count += 1
        return self.result


def test_generate_document_creates_document_with_initial_version(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    document_repo = DocumentRepository(engine)
    version_repo = DocumentVersionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Added project documentation.",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="The project includes documentation.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repo.save(claim)

    generator = RecordingDocumentGenerator(
        DocumentGenerationResult(
            content="# Test Project",
            claim_ids=[claim.id],
        )
    )

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
    assert version.content == "# Test Project"
    assert version.origin == DocumentVersionOrigin.GENERATED
    assert version.claim_ids == [claim.id]

    assert version_repo.get_by_id(version.id) == version

    received_context = generator.received_context

    assert received_context is not None
    assert received_context.project == project
    assert received_context.document == document
    assert received_context.claims == [claim]


def test_generate_document_creates_next_version_for_existing_document(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    document_repo = DocumentRepository(engine)
    version_repo = DocumentVersionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Added project documentation.",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="The project includes documentation.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repo.save(claim)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    document_repo.save(document)

    generator = StubDocumentGenerator(
        DocumentGenerationResult(
            content="# Updated Project",
            claim_ids=[claim.id],
        )
    )

    first_version = generate_document(
        project=project,
        key="readme",
        kind="readme",
        generator=generator,
        document_repository=document_repo,
        version_repository=version_repo,
        claim_repository=claim_repo,
    )

    second_version = generate_document(
        project=project,
        key="readme",
        kind="readme",
        generator=generator,
        document_repository=document_repo,
        version_repository=version_repo,
        claim_repository=claim_repo,
    )

    assert first_version.document_id == document.id
    assert first_version.version_number == 1

    assert second_version.document_id == document.id
    assert second_version.version_number == 2

    versions = version_repo.list_for_document(document.id)

    assert versions == [first_version, second_version]


def test_generate_document_rejects_project_without_active_claims(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    document_repo = DocumentRepository(engine)
    version_repo = DocumentVersionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    unavailable_claim_id = uuid4()
    generator = StubDocumentGenerator(
        DocumentGenerationResult(
            content="# Test Project",
            claim_ids=[unavailable_claim_id],
        )
    )

    with pytest.raises(NoActiveClaimsError):
        generate_document(
            project=project,
            key="readme",
            kind="readme",
            generator=generator,
            document_repository=document_repo,
            version_repository=version_repo,
            claim_repository=claim_repo,
        )

    assert generator.call_count == 0
    assert document_repo.get_by_key(project.id, "readme") is None


def test_generate_document_passes_only_active_claims_to_generator(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    document_repo = DocumentRepository(engine)
    version_repo = DocumentVersionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Project change",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    active_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Active claim",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    corrected_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Corrected claim",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.CORRECTED,
        evidence_ids=[evidence.id],
    )
    invalidated_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Invalidated claim",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.LOW,
        status=ClaimStatus.INVALIDATED,
        evidence_ids=[evidence.id],
    )

    claim_repo.save(active_claim)
    claim_repo.save(corrected_claim)
    claim_repo.save(invalidated_claim)

    generator = RecordingDocumentGenerator(
        DocumentGenerationResult(
            content="# Test Project",
            claim_ids=[active_claim.id],
        )
    )

    generate_document(
        project=project,
        key="readme",
        kind="readme",
        generator=generator,
        document_repository=document_repo,
        version_repository=version_repo,
        claim_repository=claim_repo,
    )

    received_context = generator.received_context

    assert received_context is not None
    assert received_context.claims == [active_claim]


def test_generate_document_rejects_unavailable_generated_claim(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    document_repo = DocumentRepository(engine)
    version_repo = DocumentVersionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Project change",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Available claim",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repo.save(claim)

    unavailable_claim_id = uuid4()

    generator = StubDocumentGenerator(
        DocumentGenerationResult(
            content="# Unsupported Project",
            claim_ids=[unavailable_claim_id],
        )
    )

    with pytest.raises(InvalidGeneratedClaimError):
        generate_document(
            project=project,
            key="readme",
            kind="readme",
            generator=generator,
            document_repository=document_repo,
            version_repository=version_repo,
            claim_repository=claim_repo,
        )

    assert document_repo.get_by_key(project.id, "readme") is None


def test_generate_document_preserves_selected_claim_provenance(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    document_repo = DocumentRepository(engine)
    version_repo = DocumentVersionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Project change",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    first_claim = KnowledgeClaim(
        project_id=project.id,
        statement="First active claim",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    second_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Second active claim",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    claim_repo.save(first_claim)
    claim_repo.save(second_claim)

    generator = StubDocumentGenerator(
        DocumentGenerationResult(
            content="# Test Project",
            claim_ids=[second_claim.id],
        )
    )

    version = generate_document(
        project=project,
        key="readme",
        kind="readme",
        generator=generator,
        document_repository=document_repo,
        version_repository=version_repo,
        claim_repository=claim_repo,
    )

    assert version.claim_ids == [second_claim.id]

    persisted_version = version_repo.get_by_id(version.id)

    assert persisted_version is not None
    assert persisted_version.claim_ids == [second_claim.id]


def test_generate_document_preserves_existing_document_kind(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    document_repo = DocumentRepository(engine)
    version_repo = DocumentVersionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Project change",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="The project includes documentation.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repo.save(claim)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    document_repo.save(document)

    generator = RecordingDocumentGenerator(
        DocumentGenerationResult(
            content="# Test Project",
            claim_ids=[claim.id],
        )
    )

    generate_document(
        project=project,
        key="readme",
        kind="architecture",
        generator=generator,
        document_repository=document_repo,
        version_repository=version_repo,
        claim_repository=claim_repo,
    )

    persisted_document = document_repo.get_by_id(document.id)

    assert persisted_document is not None
    assert persisted_document.kind == "readme"

    received_context = generator.received_context

    assert received_context is not None
    assert received_context.document.kind == "readme"
