"""
Integrated tests for Quilchoom's Git commit capture process.
"""

import subprocess
from datetime import UTC

from sqlalchemy import create_engine

from quilchoom.application.capture_commit import capture_commit
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    EvidenceRepository,
    ProjectRepository,
)


def test_capture_commit_persists_event_and_evidence(tmp_path):
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    (tmp_path / "README.md").write_text("# My project\n")

    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    sha = result.stdout.strip()

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)

    event_repo = EventRepository(db_engine)
    evidence_repo = EvidenceRepository(db_engine)

    event, evidence = capture_commit(
        project=project,
        repository_path=tmp_path,
        commit_sha=sha,
        event_repository=event_repo,
        evidence_repository=evidence_repo,
    )

    assert event.project_id == project.id
    assert event.type == "git_commit"
    assert event.timestamp.tzinfo is UTC
    assert event.summary == "Initial commit"
    assert event.source == "git"
    assert event.source_reference == sha

    assert evidence.project_id == project.id
    assert evidence.type == "git_diff"
    assert evidence.reference == sha
    assert evidence.source == "git"
    assert evidence.captured_at.tzinfo is UTC
    assert evidence.content != ""


def test_capture_commit_is_idempotent(tmp_path):
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    (tmp_path / "README.md").write_text("# My project\n")

    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    sha = result.stdout.strip()

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path,
    )
    project_repository = ProjectRepository(db_engine)
    project_repository.save(project)

    event_repository = EventRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)

    first_event, first_evidence = capture_commit(
        project=project,
        repository_path=tmp_path,
        commit_sha=sha,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )

    second_event, second_evidence = capture_commit(
        project=project,
        repository_path=tmp_path,
        commit_sha=sha,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )

    assert second_event.id == first_event.id
    assert second_evidence.id == first_evidence.id

    events = event_repository.list_for_project(project.id)
    evidence = evidence_repository.list_for_project(project.id)

    assert len(events) == 1
    assert len(evidence) == 1
