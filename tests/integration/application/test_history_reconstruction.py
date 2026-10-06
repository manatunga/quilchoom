"""
Integration tests for Quilchoom's development history reconstruction.
"""

from datetime import UTC, datetime

from sqlalchemy import create_engine

from quilchoom.application.reconstruct_history import reconstruct_history
from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    EvidenceRepository,
    ProjectRepository,
)


def test_reconstruct_history_from_captured_events_and_evidence(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)

    event_1 = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        summary="Add initial implementation",
        source="git",
        source_reference="commit-1",
    )

    event_2 = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        summary="Fix implementation",
        source="git",
        source_reference="commit-2",
    )

    evidence_1 = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff for commit 1",
        reference="commit-1",
        captured_at=datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
        source="git",
    )

    evidence_2 = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff for commit 2",
        reference="commit-2",
        captured_at=datetime(2026, 1, 1, 11, 1, tzinfo=UTC),
        source="git",
    )

    event_repo = EventRepository(db_engine)
    event_repo.save(event_2)
    event_repo.save(event_1)

    evidence_repo = EvidenceRepository(db_engine)
    evidence_repo.save(evidence_2)
    evidence_repo.save(evidence_1)

    history = reconstruct_history(
        project=project,
        event_repository=event_repo,
        evidence_repository=evidence_repo,
    )

    assert history.project_id == project.id
    assert len(history.entries) == 2

    assert history.entries[0].event == event_1
    assert history.entries[0].evidence == evidence_1

    assert history.entries[1].event == event_2
    assert history.entries[1].evidence == evidence_2

    assert history.entries[0].evidence.content == "diff for commit 1"
    assert history.entries[1].evidence.content == "diff for commit 2"
