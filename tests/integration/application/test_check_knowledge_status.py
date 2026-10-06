"""
Integration tests for Quilchoom's pending knowledge status checks.
"""

from datetime import UTC, datetime

from sqlalchemy import create_engine

from quilchoom.application.check_knowledge_status import count_pending_evidence
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.interpretation import InterpretationRun
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    EvidenceRepository,
    InterpretationRunRepository,
    ProjectRepository,
)


def test_count_pending_evidence_returns_zero_without_evidence(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    pending_count = count_pending_evidence(
        project=project,
        evidence_repository=EvidenceRepository(engine),
        run_repository=InterpretationRunRepository(engine),
    )

    assert pending_count == 0


def test_count_pending_evidence_counts_uninterpreted_evidence(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

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

    pending_count = count_pending_evidence(
        project=project,
        evidence_repository=evidence_repo,
        run_repository=InterpretationRunRepository(engine),
    )

    assert pending_count == 2


def test_count_pending_evidence_excludes_interpreted_evidence(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    evidence_repo = EvidenceRepository(engine)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="interpreted diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    run_repo = InterpretationRunRepository(engine)
    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence.id],
        claim_ids=[],
    )
    run_repo.save_with_claims(run, [])

    pending_count = count_pending_evidence(
        project=project,
        evidence_repository=evidence_repo,
        run_repository=run_repo,
    )

    assert pending_count == 0


def test_count_pending_evidence_counts_only_uninterpreted_evidence(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    evidence_repo = EvidenceRepository(engine)

    interpreted_evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="interpreted diff",
        captured_at=datetime.now(UTC),
        source="git",
    )
    pending_evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="pending diff",
        captured_at=datetime.now(UTC),
        source="git",
    )

    evidence_repo.save(interpreted_evidence)
    evidence_repo.save(pending_evidence)

    run_repo = InterpretationRunRepository(engine)
    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[interpreted_evidence.id],
        claim_ids=[],
    )
    run_repo.save_with_claims(run, [])

    pending_count = count_pending_evidence(
        project=project,
        evidence_repository=evidence_repo,
        run_repository=run_repo,
    )

    assert pending_count == 1
