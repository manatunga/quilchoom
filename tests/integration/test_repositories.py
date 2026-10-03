"""
Integration tests for Quilchoom's database repositories.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quilchoom.domain.correction import Correction
from quilchoom.domain.document import (
    Document,
    DocumentVersion,
    DocumentVersionOrigin,
)
from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.interpretation import InterpretationRun
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.errors import (
    DocumentNotFoundError,
    EvidenceNotFoundError,
    EvidenceProjectMismatchError,
    InvalidInterpretationRunError,
    KnowledgeClaimNotFoundError,
    KnowledgeClaimProjectMismatchError,
)
from quilchoom.infrastructure.database.models import Base, ProjectModel
from quilchoom.infrastructure.database.repositories import (
    CorrectionRepository,
    DocumentRepository,
    DocumentVersionRepository,
    EventRepository,
    EvidenceRepository,
    InterpretationRunRepository,
    KnowledgeClaimRepository,
    ProjectRepository,
)


def test_project_save(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    repository = ProjectRepository(db_engine)
    repository.save(project)

    with Session(db_engine) as session:
        model = session.scalars(
            select(ProjectModel).where(ProjectModel.id == str(project.id))
        ).first()

        assert model is not None

        db_values = {
            col.name: getattr(model, col.name) for col in ProjectModel.__table__.columns
        }
        domain_values = project.model_dump()
        domain_values["id"] = str(domain_values["id"])
        domain_values["repository_path"] = str(domain_values["repository_path"])

        assert db_values == domain_values


def test_project_repo_get_by_id_on_existing_project(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    repository = ProjectRepository(db_engine)
    repository.save(project)

    retrieved = repository.get_by_id(project.id)

    assert retrieved == project


def test_project_repo_get_by_id_on_non_existent_project():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    repository = ProjectRepository(db_engine)

    retrieved = repository.get_by_id(uuid4())

    assert retrieved is None


def test_project_repo_get_by_repository_path_on_existing_project(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    repository = ProjectRepository(db_engine)
    repository.save(project)

    retrieved = repository.get_by_repository_path(project.repository_path)

    assert retrieved == project


def test_project_repo_get_by_repository_path_on_unknown_path(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    repository = ProjectRepository(db_engine)

    retrieved = repository.get_by_repository_path(tmp_path)

    assert retrieved is None


def test_event_repo_save_and_get_event(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
        summary="Added event persistence",
        source="git",
        source_reference="abc123",
    )
    event_repo = EventRepository(db_engine)
    event_repo.save(event)

    retrieved = event_repo.get_by_id(event.id)

    assert retrieved == event


def test_event_repo_get_by_id_on_non_existent_event():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    repository = EventRepository(db_engine)

    retrieved = repository.get_by_id(uuid4())

    assert retrieved is None


def test_event_repo_list_events_for_project(tmp_path):
    path1 = tmp_path / "project1"
    path2 = tmp_path / "project2"

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="project1", repository_path=path1)
    other_project = Project(name="project2", repository_path=path2)

    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)
    project_repo.save(other_project)

    event_a = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 14, 0, tzinfo=UTC),
        summary="Added event persistence",
        source="git",
        source_reference="abc123",
    )
    event_b = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
        summary="Added evidence persistence",
        source="git",
        source_reference="a1b2c3",
    )
    event_c = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 13, 0, tzinfo=UTC),
        summary="Added alembic migration schema",
        source="git",
        source_reference="b3gh4s",
    )
    other_project_event = Event(
        project_id=other_project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 11, 0, tzinfo=UTC),
        summary="Added event persistence",
        source="git",
        source_reference="akl343",
    )

    event_repo = EventRepository(db_engine)
    event_repo.save(event_a)
    event_repo.save(event_b)
    event_repo.save(event_c)
    event_repo.save(other_project_event)

    events = event_repo.list_for_project(project.id)

    assert events == [event_b, event_c, event_a]


def test_event_get_by_source_reference(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
        summary="Added event persistence",
        source="git",
        source_reference="abc123",
    )
    event_repo = EventRepository(db_engine)
    event_repo.save(event)

    retrieved = event_repo.get_by_source_reference(
        project.id, event.source, event.source_reference
    )

    assert retrieved == event

    fail_retrieved = event_repo.get_by_source_reference(
        project.id, event.source, "a1b2c3d"
    )

    assert fail_retrieved is None


def test_save_and_get_evidence(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)

    captured_at = datetime.now(UTC)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git ...",
        reference="abc123",
        captured_at=captured_at,
        source="git",
    )

    evidence_repo = EvidenceRepository(db_engine)
    evidence_repo.save(evidence)

    retrieved = evidence_repo.get_by_id(evidence.id)

    assert retrieved == evidence


def test_evidence_get_by_id_returns_none_for_nonexistent_evidence(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    evidence_repo = EvidenceRepository(db_engine)

    assert evidence_repo.get_by_id(uuid4()) is None


def test_evidence_get_by_source_reference(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)

    captured_at = datetime.now(UTC)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git ...",
        reference="abc123",
        captured_at=captured_at,
        source="git",
    )

    evidence_repo = EvidenceRepository(db_engine)
    evidence_repo.save(evidence)

    reference = evidence.reference

    assert reference is not None

    retrieved = evidence_repo.get_by_reference(project.id, evidence.source, reference)

    assert retrieved == evidence

    fail_retrieved = evidence_repo.get_by_reference(
        project.id, evidence.source, "a1b2c3d"
    )

    assert fail_retrieved is None


def test_list_evidence_for_project(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(
        name="my_project",
        repository_path=(tmp_path / "my_project"),
    )
    other_project = Project(
        name="other_project",
        repository_path=(tmp_path / "other_project"),
    )

    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)
    project_repo.save(other_project)

    evidence_repo = EvidenceRepository(db_engine)

    later_evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="later",
        captured_at=datetime(2026, 9, 30, 14, 0, tzinfo=UTC),
        source="git",
    )
    earlier_evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="earlier",
        captured_at=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
        source="git",
    )
    other_evidence = Evidence(
        project_id=other_project.id,
        type="git_diff",
        content="other project",
        captured_at=datetime(2026, 9, 30, 11, 0, tzinfo=UTC),
        source="git",
    )

    evidence_repo.save(later_evidence)
    evidence_repo.save(other_evidence)
    evidence_repo.save(earlier_evidence)

    evidence = evidence_repo.list_for_project(project.id)

    assert evidence == [earlier_evidence, later_evidence]


def test_save_and_get_knowledge_claim(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path,
    )
    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git ...",
        reference="abc123",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo = EvidenceRepository(db_engine)
    evidence_repo.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="The project added knowledge claim persistence.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    claim_repo = KnowledgeClaimRepository(db_engine)
    claim_repo.save(claim)

    retrieved = claim_repo.get_by_id(claim.id)

    assert retrieved == claim


def test_knowledge_claim_get_by_id_returns_none_for_nonexistent_claim():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    claim_repo = KnowledgeClaimRepository(db_engine)

    assert claim_repo.get_by_id(uuid4()) is None


def test_knowledge_claim_supports_multiple_evidence(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(db_engine).save(project)

    evidence_repo = EvidenceRepository(db_engine)

    evidence_a = Evidence(
        project_id=project.id,
        type="git_diff",
        content="first diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_b = Evidence(
        project_id=project.id,
        type="git_diff",
        content="second diff",
        captured_at=datetime.now(UTC),
        source="git",
    )

    evidence_repo.save(evidence_a)
    evidence_repo.save(evidence_b)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="A change is supported by multiple pieces of evidence.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_a.id, evidence_b.id],
    )

    claim_repo = KnowledgeClaimRepository(db_engine)
    claim_repo.save(claim)

    retrieved = claim_repo.get_by_id(claim.id)

    assert retrieved is not None
    assert set(retrieved.evidence_ids) == {evidence_a.id, evidence_b.id}


def test_knowledge_claim_save_rejects_missing_evidence(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(db_engine).save(project)

    missing_evidence_id = uuid4()

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Unsupported claim.",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.LOW,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[missing_evidence_id],
    )

    claim_repo = KnowledgeClaimRepository(db_engine)

    with pytest.raises(EvidenceNotFoundError):
        claim_repo.save(claim)

    assert claim_repo.get_by_id(claim.id) is None


def test_knowledge_claim_save_rejects_evidence_from_different_project(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path / "my_project",
    )
    other_project = Project(
        name="other_project",
        repository_path=tmp_path / "other_project",
    )

    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)
    project_repo.save(other_project)

    evidence = Evidence(
        project_id=other_project.id,
        type="git_diff",
        content="unrelated diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo = EvidenceRepository(db_engine)
    evidence_repo.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Claim for the first project.",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    claim_repo = KnowledgeClaimRepository(db_engine)

    with pytest.raises(EvidenceProjectMismatchError):
        claim_repo.save(claim)

    assert claim_repo.get_by_id(claim.id) is None


def test_list_knowledge_claims_for_project(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(
        name="my_project",
        repository_path=(tmp_path / "my_project"),
    )
    other_project = Project(
        name="other_project",
        repository_path=(tmp_path / "other_project"),
    )

    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)
    project_repo.save(other_project)

    evidence_a = Evidence(
        project_id=project.id,
        type="git_diff",
        content="first diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_b = Evidence(
        project_id=other_project.id,
        type="git_diff",
        content="second diff",
        captured_at=datetime.now(UTC),
        source="git",
    )

    evidence_repo = EvidenceRepository(db_engine)
    evidence_repo.save(evidence_a)
    evidence_repo.save(evidence_b)

    claim_a = KnowledgeClaim(
        project_id=project.id,
        statement="Git capture was made idempotent",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_a.id],
    )
    claim_b = KnowledgeClaim(
        project_id=other_project.id,
        statement="Alembic migrations were added for SQLAlchemy models",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.INVALIDATED,
        evidence_ids=[evidence_b.id],
    )

    claim_repo = KnowledgeClaimRepository(db_engine)
    claim_repo.save(claim_a)
    claim_repo.save(claim_b)

    claims = claim_repo.list_for_project(project.id)

    assert claims == [claim_a]


def test_save_and_get_correction(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    correction_repo = CorrectionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    captured_at = datetime.now(UTC)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Test evidence",
        reference="a1b2c3d",
        captured_at=captured_at,
        source="git",
    )
    evidence_repo.save(evidence)

    target_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Original interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    replacement_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Corrected interpretation",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    claim_repo.save(target_claim)
    claim_repo.save(replacement_claim)

    correction = Correction(
        project_id=project.id,
        target_claim_id=target_claim.id,
        reason="The original interpretation was incomplete.",
        replacement_claim_id=replacement_claim.id,
    )

    correction_repo.save(correction)

    retrieved = correction_repo.get_by_id(correction.id)

    assert retrieved == correction


def test_correction_get_by_id_returns_none_for_nonexistent_correction():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    correction_repo = CorrectionRepository(engine)

    assert correction_repo.get_by_id(uuid4()) is None


def test_list_corrections_for_project(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    correction_repo = CorrectionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path / "test-project",
    )
    other_project = Project(
        name="Other Project",
        repository_path=tmp_path / "other-project",
    )

    project_repo.save(project)
    project_repo.save(other_project)

    captured_at = datetime.now(UTC)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Test evidence",
        source="git",
        captured_at=captured_at,
    )
    other_evidence = Evidence(
        project_id=other_project.id,
        type="git_diff",
        content="Other evidence",
        source="git",
        captured_at=captured_at,
    )

    evidence_repo.save(evidence)
    evidence_repo.save(other_evidence)

    target_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Original interpretation",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    other_target_claim = KnowledgeClaim(
        project_id=other_project.id,
        statement="Other interpretation",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[other_evidence.id],
    )

    claim_repo.save(target_claim)
    claim_repo.save(other_target_claim)

    correction = Correction(
        project_id=project.id,
        target_claim_id=target_claim.id,
        reason="Reason for correction",
    )
    other_correction = Correction(
        project_id=other_project.id,
        target_claim_id=other_target_claim.id,
        reason="Reason for other correction",
    )

    correction_repo.save(correction)
    correction_repo.save(other_correction)

    corrections = correction_repo.list_for_project(project.id)

    assert corrections == [correction]


def test_save_correction_with_claim_status_update(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    correction_repo = CorrectionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    captured_at = datetime.now(UTC)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Test evidence",
        source="git",
        captured_at=captured_at,
    )
    evidence_repo.save(evidence)

    target_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Original interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    replacement_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Corrected interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    claim_repo.save(target_claim)
    claim_repo.save(replacement_claim)

    correction = Correction(
        project_id=project.id,
        target_claim_id=target_claim.id,
        reason="The original interpretation was incomplete.",
        replacement_claim_id=replacement_claim.id,
    )

    correction_repo.save_with_claim_status_update(
        correction,
        ClaimStatus.CORRECTED,
    )

    retrieved_claim = claim_repo.get_by_id(target_claim.id)
    retrieved_correction = correction_repo.get_by_id(correction.id)

    assert retrieved_claim is not None
    assert retrieved_claim.status == ClaimStatus.CORRECTED
    assert retrieved_correction == correction


def test_save_correction_with_claim_invalidation(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    correction_repo = CorrectionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    captured_at = datetime.now(UTC)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Test evidence",
        source="git",
        captured_at=captured_at,
    )
    evidence_repo.save(evidence)

    target_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Unsupported interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repo.save(target_claim)

    correction = Correction(
        project_id=project.id,
        target_claim_id=target_claim.id,
        reason="The interpretation is no longer supported.",
    )

    correction_repo.save_with_claim_status_update(
        correction,
        ClaimStatus.INVALIDATED,
    )

    retrieved_claim = claim_repo.get_by_id(target_claim.id)
    retrieved_correction = correction_repo.get_by_id(correction.id)

    assert retrieved_claim is not None
    assert retrieved_claim.status == ClaimStatus.INVALIDATED
    assert retrieved_correction is not None
    assert retrieved_correction == correction
    assert retrieved_correction.replacement_claim_id is None


def test_save_correction_with_status_update_rejects_missing_target():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    correction_repo = CorrectionRepository(engine)

    correction = Correction(
        project_id=uuid4(),
        target_claim_id=uuid4(),
        reason="Reason for correction",
    )

    with pytest.raises(KnowledgeClaimNotFoundError):
        correction_repo.save_with_claim_status_update(
            correction,
            ClaimStatus.INVALIDATED,
        )

    assert correction_repo.get_by_id(correction.id) is None


def test_save_correction_with_status_update_rolls_back_on_failure(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project_repo = ProjectRepository(engine)
    evidence_repo = EvidenceRepository(engine)
    claim_repo = KnowledgeClaimRepository(engine)
    correction_repo = CorrectionRepository(engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    captured_at = datetime.now(UTC)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Test evidence",
        source="git",
        captured_at=captured_at,
    )
    evidence_repo.save(evidence)

    target_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Original interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    claim_repo.save(target_claim)

    correction = Correction(
        project_id=project.id,
        target_claim_id=target_claim.id,
        reason="Reason for correction",
    )

    correction_repo.save(correction)

    with pytest.raises(IntegrityError):
        correction_repo.save_with_claim_status_update(
            correction,
            ClaimStatus.INVALIDATED,
        )

    retrieved_claim = claim_repo.get_by_id(target_claim.id)

    assert retrieved_claim is not None
    assert retrieved_claim.status == ClaimStatus.ACTIVE


def test_save_and_get_document(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )

    document_repo = DocumentRepository(engine)
    document_repo.save(document)

    retrieved = document_repo.get_by_id(document.id)

    assert retrieved == document


def test_document_get_by_id_returns_none_for_nonexistent_document():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    document_repo = DocumentRepository(engine)

    assert document_repo.get_by_id(uuid4()) is None


def test_document_get_by_key(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )

    document_repo = DocumentRepository(engine)
    document_repo.save(document)

    retrieved = document_repo.get_by_key(project.id, "readme")

    assert retrieved == document
    assert document_repo.get_by_key(project.id, "architecture") is None


def test_document_get_by_key_is_scoped_to_project(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path / "my_project",
    )
    other_project = Project(
        name="other_project",
        repository_path=tmp_path / "other_project",
    )

    project_repo = ProjectRepository(engine)
    project_repo.save(project)
    project_repo.save(other_project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    other_document = Document(
        project_id=other_project.id,
        key="readme",
        kind="readme",
    )

    document_repo = DocumentRepository(engine)
    document_repo.save(document)
    document_repo.save(other_document)

    assert document_repo.get_by_key(project.id, "readme") == document
    assert document_repo.get_by_key(other_project.id, "readme") == other_document


def test_list_documents_for_project(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path / "my_project",
    )
    other_project = Project(
        name="other_project",
        repository_path=tmp_path / "other_project",
    )

    project_repo = ProjectRepository(engine)
    project_repo.save(project)
    project_repo.save(other_project)

    earlier_document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
        created_at=datetime(2026, 10, 2, 12, 0, tzinfo=UTC),
    )
    later_document = Document(
        project_id=project.id,
        key="architecture",
        kind="architecture",
        created_at=datetime(2026, 10, 2, 14, 0, tzinfo=UTC),
    )
    other_document = Document(
        project_id=other_project.id,
        key="readme",
        kind="readme",
        created_at=datetime(2026, 10, 2, 11, 0, tzinfo=UTC),
    )

    document_repo = DocumentRepository(engine)
    document_repo.save(later_document)
    document_repo.save(other_document)
    document_repo.save(earlier_document)

    documents = document_repo.list_for_project(project.id)

    assert documents == [earlier_document, later_document]


def test_save_and_get_document_version(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    DocumentRepository(engine).save(document)

    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# My Project",
        origin=DocumentVersionOrigin.GENERATED,
    )

    version_repo = DocumentVersionRepository(engine)
    version_repo.save(version)

    retrieved = version_repo.get_by_id(version.id)

    assert retrieved == version


def test_document_version_get_by_id_returns_none_for_nonexistent_version():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    version_repo = DocumentVersionRepository(engine)

    assert version_repo.get_by_id(uuid4()) is None


def test_document_version_supports_claim_provenance(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff --git ...",
        captured_at=datetime.now(UTC),
        source="git",
    )
    EvidenceRepository(engine).save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="The project added documentation support.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    KnowledgeClaimRepository(engine).save(claim)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    DocumentRepository(engine).save(document)

    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# My Project",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim.id],
    )

    version_repo = DocumentVersionRepository(engine)
    version_repo.save(version)

    retrieved = version_repo.get_by_id(version.id)

    assert retrieved == version


def test_document_version_save_rejects_missing_document():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    version = DocumentVersion(
        document_id=uuid4(),
        version_number=1,
        content="# Missing Document",
        origin=DocumentVersionOrigin.GENERATED,
    )

    version_repo = DocumentVersionRepository(engine)

    with pytest.raises(DocumentNotFoundError):
        version_repo.save(version)

    assert version_repo.get_by_id(version.id) is None


def test_document_version_save_rejects_missing_claim(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    DocumentRepository(engine).save(document)

    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# My Project",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[uuid4()],
    )

    version_repo = DocumentVersionRepository(engine)

    with pytest.raises(KnowledgeClaimNotFoundError):
        version_repo.save(version)

    assert version_repo.get_by_id(version.id) is None


def test_document_version_save_rejects_claim_from_different_project(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path / "my_project",
    )
    other_project = Project(
        name="other_project",
        repository_path=tmp_path / "other_project",
    )

    project_repo = ProjectRepository(engine)
    project_repo.save(project)
    project_repo.save(other_project)

    evidence = Evidence(
        project_id=other_project.id,
        type="git_diff",
        content="unrelated diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    EvidenceRepository(engine).save(evidence)

    claim = KnowledgeClaim(
        project_id=other_project.id,
        statement="Claim belonging to another project.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )
    KnowledgeClaimRepository(engine).save(claim)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    DocumentRepository(engine).save(document)

    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# My Project",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim.id],
    )

    version_repo = DocumentVersionRepository(engine)

    with pytest.raises(KnowledgeClaimProjectMismatchError):
        version_repo.save(version)

    assert version_repo.get_by_id(version.id) is None


def test_list_document_versions_in_version_order(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    DocumentRepository(engine).save(document)

    version_one = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# Version 1",
        origin=DocumentVersionOrigin.GENERATED,
    )
    version_two = DocumentVersion(
        document_id=document.id,
        version_number=2,
        content="# Version 2",
        origin=DocumentVersionOrigin.MANUAL,
    )

    version_repo = DocumentVersionRepository(engine)
    version_repo.save(version_two)
    version_repo.save(version_one)

    versions = version_repo.list_for_document(document.id)

    assert versions == [version_one, version_two]


def test_get_latest_document_version(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    DocumentRepository(engine).save(document)

    version_one = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# Version 1",
        origin=DocumentVersionOrigin.GENERATED,
    )
    version_two = DocumentVersion(
        document_id=document.id,
        version_number=2,
        content="# Version 2",
        origin=DocumentVersionOrigin.MANUAL,
    )

    version_repo = DocumentVersionRepository(engine)
    version_repo.save(version_one)
    version_repo.save(version_two)

    assert version_repo.get_latest(document.id) == version_two


def test_get_latest_document_version_returns_none_when_no_versions(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    DocumentRepository(engine).save(document)

    version_repo = DocumentVersionRepository(engine)

    assert version_repo.get_latest(document.id) is None


def test_interpretation_run_save_with_claims_persists_claims_and_provenance(
    tmp_path,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(engine)
    project_repo.save(project)

    evidence_repo = EvidenceRepository(engine)

    evidence_a = Evidence(
        project_id=project.id,
        type="git_diff",
        content="first diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_b = Evidence(
        project_id=project.id,
        type="git_diff",
        content="second diff",
        captured_at=datetime.now(UTC),
        source="git",
    )

    evidence_repo.save(evidence_a)
    evidence_repo.save(evidence_b)

    claim_a = KnowledgeClaim(
        project_id=project.id,
        statement="The project added interpretation persistence.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_a.id],
    )
    claim_b = KnowledgeClaim(
        project_id=project.id,
        statement="The changes support knowledge interpretation.",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_a.id, evidence_b.id],
    )

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence_a.id, evidence_b.id],
        claim_ids=[claim_a.id, claim_b.id],
    )

    run_repo = InterpretationRunRepository(engine)
    run_repo.save_with_claims(run, [claim_a, claim_b])

    claim_repo = KnowledgeClaimRepository(engine)

    retrieved_claim_a = claim_repo.get_by_id(claim_a.id)
    retrieved_claim_b = claim_repo.get_by_id(claim_b.id)

    assert retrieved_claim_a is not None
    assert retrieved_claim_b is not None

    assert set(retrieved_claim_a.evidence_ids) == {evidence_a.id}
    assert set(retrieved_claim_b.evidence_ids) == {
        evidence_a.id,
        evidence_b.id,
    }

    assert run_repo.list_interpreted_evidence_ids(project.id) == {
        evidence_a.id,
        evidence_b.id,
    }


def test_interpretation_run_save_with_zero_claims_marks_evidence_interpreted(
    tmp_path,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(engine)
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff with no useful claim",
        captured_at=datetime.now(UTC),
        source="git",
    )
    EvidenceRepository(engine).save(evidence)

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence.id],
        claim_ids=[],
    )

    run_repo = InterpretationRunRepository(engine)
    run_repo.save_with_claims(run, [])

    assert run_repo.list_interpreted_evidence_ids(project.id) == {evidence.id}


def test_list_interpreted_evidence_ids_is_scoped_to_project(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path / "my_project",
    )
    other_project = Project(
        name="other_project",
        repository_path=tmp_path / "other_project",
    )

    project_repo = ProjectRepository(engine)
    project_repo.save(project)
    project_repo.save(other_project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="project diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    other_evidence = Evidence(
        project_id=other_project.id,
        type="git_diff",
        content="other project diff",
        captured_at=datetime.now(UTC),
        source="git",
    )

    evidence_repo = EvidenceRepository(engine)
    evidence_repo.save(evidence)
    evidence_repo.save(other_evidence)

    run_repo = InterpretationRunRepository(engine)

    run_repo.save_with_claims(
        InterpretationRun(
            project_id=project.id,
            evidence_ids=[evidence.id],
        ),
        [],
    )
    run_repo.save_with_claims(
        InterpretationRun(
            project_id=other_project.id,
            evidence_ids=[other_evidence.id],
        ),
        [],
    )

    assert run_repo.list_interpreted_evidence_ids(project.id) == {evidence.id}
    assert run_repo.list_interpreted_evidence_ids(other_project.id) == {
        other_evidence.id
    }


def test_interpretation_run_save_rejects_missing_evidence(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(engine)
    project_repo.save(project)

    missing_evidence_id = uuid4()

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[missing_evidence_id],
    )

    run_repo = InterpretationRunRepository(engine)

    with pytest.raises(EvidenceNotFoundError):
        run_repo.save_with_claims(run, [])

    assert run_repo.list_interpreted_evidence_ids(project.id) == set()


def test_interpretation_run_save_rejects_evidence_from_different_project(
    tmp_path,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path / "my_project",
    )
    other_project = Project(
        name="other_project",
        repository_path=tmp_path / "other_project",
    )

    project_repo = ProjectRepository(engine)
    project_repo.save(project)
    project_repo.save(other_project)

    evidence = Evidence(
        project_id=other_project.id,
        type="git_diff",
        content="unrelated diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo = EvidenceRepository(engine)
    evidence_repo.save(evidence)

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence.id],
    )

    run_repo = InterpretationRunRepository(engine)

    with pytest.raises(EvidenceProjectMismatchError):
        run_repo.save_with_claims(run, [])

    assert run_repo.list_interpreted_evidence_ids(project.id) == set()


def test_interpretation_run_save_rejects_claim_id_mismatch(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(engine)
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="test diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo = EvidenceRepository(engine)
    evidence_repo.save(evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="A claim not declared by the run.",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence.id],
        claim_ids=[],
    )

    run_repo = InterpretationRunRepository(engine)

    with pytest.raises(InvalidInterpretationRunError):
        run_repo.save_with_claims(run, [claim])

    assert KnowledgeClaimRepository(engine).get_by_id(claim.id) is None


def test_interpretation_run_save_rejects_claim_from_different_project(
    tmp_path,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path / "my_project",
    )
    other_project = Project(
        name="other_project",
        repository_path=tmp_path / "other_project",
    )

    project_repo = ProjectRepository(engine)
    project_repo.save(project)
    project_repo.save(other_project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="test diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    EvidenceRepository(engine).save(evidence)

    claim = KnowledgeClaim(
        project_id=other_project.id,
        statement="Claim belonging to another project.",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence.id],
        claim_ids=[claim.id],
    )

    run_repo = InterpretationRunRepository(engine)

    with pytest.raises(InvalidInterpretationRunError):
        run_repo.save_with_claims(run, [claim])

    assert KnowledgeClaimRepository(engine).get_by_id(claim.id) is None


def test_interpretation_run_save_rejects_claim_evidence_outside_run(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(engine)
    project_repo.save(project)

    evidence_repo = EvidenceRepository(engine)

    run_evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="interpreted diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    outside_evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="different diff",
        captured_at=datetime.now(UTC),
        source="git",
    )

    evidence_repo.save(run_evidence)
    evidence_repo.save(outside_evidence)

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Claim cites evidence outside this run.",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[outside_evidence.id],
    )

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[run_evidence.id],
        claim_ids=[claim.id],
    )

    run_repo = InterpretationRunRepository(engine)

    with pytest.raises(InvalidInterpretationRunError):
        run_repo.save_with_claims(run, [claim])

    assert KnowledgeClaimRepository(engine).get_by_id(claim.id) is None


def test_interpretation_run_save_with_claims_rolls_back_on_failure(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(engine)
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="test diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo = EvidenceRepository(engine)
    evidence_repo.save(evidence)

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence.id],
    )
    run_repo = InterpretationRunRepository(engine)
    run_repo.save_with_claims(run, [])

    claim = KnowledgeClaim(
        project_id=project.id,
        statement="This claim should be rolled back.",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence.id],
    )

    second_run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence.id],
        claim_ids=[claim.id],
    )

    with pytest.raises(IntegrityError):
        run_repo.save_with_claims(second_run, [claim])

    claim_repo = KnowledgeClaimRepository(engine)
    retrieved_claim = claim_repo.get_by_id(claim.id)

    assert retrieved_claim is None
