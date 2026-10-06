"""
Integration tests for Quilchoom's Git repository capture process.
"""

import subprocess

from sqlalchemy import create_engine

from quilchoom.application.capture_commit import capture_commit
from quilchoom.application.capture_repository import capture_repository
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    EvidenceRepository,
    ProjectRepository,
)
from tests.helpers.git import initialize_git_repository


def create_commit(tmp_path, filename: str, content: str, message: str) -> str:
    (tmp_path / filename).write_text(content)

    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
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

    return result.stdout.strip()


def create_capture_context(tmp_path):
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

    return project, event_repository, evidence_repository


def test_capture_repository_captures_all_commits(tmp_path):
    initialize_git_repository(tmp_path)

    first_sha = create_commit(
        tmp_path,
        "first.txt",
        "first\n",
        "First commit",
    )
    second_sha = create_commit(
        tmp_path,
        "second.txt",
        "second\n",
        "Second commit",
    )
    third_sha = create_commit(
        tmp_path,
        "third.txt",
        "third\n",
        "Third commit",
    )

    project, event_repository, evidence_repository = create_capture_context(tmp_path)

    result = capture_repository(
        project=project,
        repository_path=tmp_path,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )

    events = event_repository.list_for_project(project.id)
    evidence = evidence_repository.list_for_project(project.id)

    assert result.discovered_commits == 3
    assert result.captured_commits == 3

    assert [event.source_reference for event in events] == [
        first_sha,
        second_sha,
        third_sha,
    ]
    assert [item.reference for item in evidence] == [
        first_sha,
        second_sha,
        third_sha,
    ]


def test_capture_repository_captures_only_uncaptured_commits(tmp_path):
    initialize_git_repository(tmp_path)

    first_sha = create_commit(
        tmp_path,
        "first.txt",
        "first\n",
        "First commit",
    )
    second_sha = create_commit(
        tmp_path,
        "second.txt",
        "second\n",
        "Second commit",
    )
    third_sha = create_commit(
        tmp_path,
        "third.txt",
        "third\n",
        "Third commit",
    )

    project, event_repository, evidence_repository = create_capture_context(tmp_path)

    capture_commit(
        project=project,
        repository_path=tmp_path,
        commit_sha=first_sha,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )
    capture_commit(
        project=project,
        repository_path=tmp_path,
        commit_sha=second_sha,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )

    result = capture_repository(
        project=project,
        repository_path=tmp_path,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )

    events = event_repository.list_for_project(project.id)
    evidence = evidence_repository.list_for_project(project.id)

    assert result.discovered_commits == 3
    assert result.captured_commits == 1

    assert [event.source_reference for event in events] == [
        first_sha,
        second_sha,
        third_sha,
    ]
    assert [item.reference for item in evidence] == [
        first_sha,
        second_sha,
        third_sha,
    ]


def test_capture_repository_is_no_op_when_current(tmp_path):
    initialize_git_repository(tmp_path)

    create_commit(
        tmp_path,
        "first.txt",
        "first\n",
        "First commit",
    )
    create_commit(
        tmp_path,
        "second.txt",
        "second\n",
        "Second commit",
    )

    project, event_repository, evidence_repository = create_capture_context(tmp_path)

    first_result = capture_repository(
        project=project,
        repository_path=tmp_path,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )

    second_result = capture_repository(
        project=project,
        repository_path=tmp_path,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )

    events = event_repository.list_for_project(project.id)
    evidence = evidence_repository.list_for_project(project.id)

    assert first_result.discovered_commits == 2
    assert first_result.captured_commits == 2

    assert second_result.discovered_commits == 2
    assert second_result.captured_commits == 0

    assert len(events) == 2
    assert len(evidence) == 2
