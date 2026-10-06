"""
Integrated tests for project workflow status determination.
"""

import subprocess
from datetime import UTC, datetime

from sqlalchemy import create_engine

from quilchoom.application.get_project_status import (
    DocumentState,
    get_project_status,
)
from quilchoom.domain.document import (
    Document,
    DocumentVersion,
    DocumentVersionOrigin,
)
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
    InterpretationRunRepository,
    KnowledgeClaimRepository,
    ProjectRepository,
)


def _create_git_repository(repository_path) -> None:
    repository_path.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=repository_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repository_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repository_path,
        capture_output=True,
        check=True,
    )


def _commit(repository_path, content: str, message: str) -> str:
    tracked_file = repository_path / "example.txt"
    tracked_file.write_text(content)

    subprocess.run(
        ["git", "add", "example.txt"],
        cwd=repository_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repository_path,
        capture_output=True,
        check=True,
    )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


def test_get_project_status_reports_empty_project(tmp_path):
    repository_path = tmp_path / "repository"
    _create_git_repository(repository_path)

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repository = ProjectRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)
    run_repository = InterpretationRunRepository(db_engine)
    claim_repository = KnowledgeClaimRepository(db_engine)
    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=repository_path,
    )
    project_repository.save(project)

    status = get_project_status(
        project=project,
        repository_root=repository_path,
        evidence_repository=evidence_repository,
        run_repository=run_repository,
        claim_repository=claim_repository,
        document_repository=document_repository,
        version_repository=version_repository,
    )

    assert status.total_commits == 0
    assert status.pending_commits == 0
    assert status.pending_evidence == 0
    assert status.active_claims == 0
    assert status.documents == []


def test_get_project_status_reports_pending_activity_and_knowledge(tmp_path):
    repository_path = tmp_path / "repository"
    _create_git_repository(repository_path)

    first_sha = _commit(repository_path, "first\n", "First commit")
    _commit(repository_path, "second\n", "Second commit")

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repository = ProjectRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)
    run_repository = InterpretationRunRepository(db_engine)
    claim_repository = KnowledgeClaimRepository(db_engine)
    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=repository_path,
    )
    project_repository.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="First captured change",
        reference=first_sha,
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repository.save(evidence)

    status = get_project_status(
        project=project,
        repository_root=repository_path,
        evidence_repository=evidence_repository,
        run_repository=run_repository,
        claim_repository=claim_repository,
        document_repository=document_repository,
        version_repository=version_repository,
    )

    assert status.total_commits == 2
    assert status.pending_commits == 1
    assert status.pending_evidence == 1
    assert status.active_claims == 0
    assert status.documents == []


def test_get_project_status_reports_current_document(tmp_path):
    repository_path = tmp_path / "repository"
    _create_git_repository(repository_path)

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repository = ProjectRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)
    run_repository = InterpretationRunRepository(db_engine)
    claim_repository = KnowledgeClaimRepository(db_engine)
    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=repository_path,
    )
    project_repository.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Project evidence",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repository.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="The project has documented behavior.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repository.save(claim)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# Test Project",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim.id],
    )
    document_repository.save_with_initial_version(document, version)

    status = get_project_status(
        project=project,
        repository_root=repository_path,
        evidence_repository=evidence_repository,
        run_repository=run_repository,
        claim_repository=claim_repository,
        document_repository=document_repository,
        version_repository=version_repository,
    )

    assert status.active_claims == 1
    assert len(status.documents) == 1

    document_status = status.documents[0]

    assert document_status.key == "readme"
    assert document_status.kind == "readme"
    assert document_status.version_number == 1
    assert document_status.state == DocumentState.CURRENT


def test_get_project_status_reports_stale_document(tmp_path):
    repository_path = tmp_path / "repository"
    _create_git_repository(repository_path)

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repository = ProjectRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)
    run_repository = InterpretationRunRepository(db_engine)
    claim_repository = KnowledgeClaimRepository(db_engine)
    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=repository_path,
    )
    project_repository.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Outdated project evidence",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repository.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="An outdated project claim.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.CORRECTED,
        evidence_ids=[evidence.id],
    )
    claim_repository.save(claim)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# Outdated README",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim.id],
    )
    document_repository.save_with_initial_version(document, version)

    status = get_project_status(
        project=project,
        repository_root=repository_path,
        evidence_repository=evidence_repository,
        run_repository=run_repository,
        claim_repository=claim_repository,
        document_repository=document_repository,
        version_repository=version_repository,
    )

    assert status.active_claims == 0
    assert len(status.documents) == 1
    assert status.documents[0].state == DocumentState.STALE


def test_get_project_status_reports_multiple_document_types(tmp_path):
    repository_path = tmp_path / "repository"
    _create_git_repository(repository_path)

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repository = ProjectRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)
    run_repository = InterpretationRunRepository(db_engine)
    claim_repository = KnowledgeClaimRepository(db_engine)
    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=repository_path,
    )
    project_repository.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Shared project evidence",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repository.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="The project has documented architecture.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repository.save(claim)

    readme = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    readme_version = DocumentVersion(
        document_id=readme.id,
        version_number=1,
        content="# README",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim.id],
    )
    document_repository.save_with_initial_version(
        readme,
        readme_version,
    )

    architecture = Document(
        project_id=project.id,
        key="architecture",
        kind="architecture",
    )
    architecture_version = DocumentVersion(
        document_id=architecture.id,
        version_number=1,
        content="# Architecture",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim.id],
    )
    document_repository.save_with_initial_version(
        architecture,
        architecture_version,
    )

    status = get_project_status(
        project=project,
        repository_root=repository_path,
        evidence_repository=evidence_repository,
        run_repository=run_repository,
        claim_repository=claim_repository,
        document_repository=document_repository,
        version_repository=version_repository,
    )

    documents_by_key = {document.key: document for document in status.documents}

    assert set(documents_by_key) == {"readme", "architecture"}

    assert documents_by_key["readme"].version_number == 1
    assert documents_by_key["readme"].state == DocumentState.CURRENT

    assert documents_by_key["architecture"].version_number == 1
    assert documents_by_key["architecture"].state == DocumentState.CURRENT
