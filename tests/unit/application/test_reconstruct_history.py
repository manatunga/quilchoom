"""
Unit tests for the development history reconstruction use case.
"""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from quilchoom.application.errors import HistoryReconstructionError
from quilchoom.application.reconstruct_history import reconstruct_history
from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    EvidenceRepository,
)


def test_reconstruct_history_success_and_orders_chronologically(tmp_path):
    project_id = uuid4()

    project = Project(
        id=project_id,
        name="test-project",
        repository_path=tmp_path,
    )

    event_1 = Event(
        project_id=project_id,
        type="git_commit",
        timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        summary="Add initial implementation",
        source="git",
        source_reference="commit-1",
    )

    event_2 = Event(
        project_id=project_id,
        type="git_commit",
        timestamp=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        summary="Fix implementation",
        source="git",
        source_reference="commit-2",
    )

    evidence_1 = Evidence(
        project_id=project_id,
        type="git_diff",
        content="diff for commit 1",
        reference="commit-1",
        captured_at=datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
        source="git",
    )

    evidence_2 = Evidence(
        project_id=project_id,
        type="git_diff",
        content="diff for commit 2",
        reference="commit-2",
        captured_at=datetime(2026, 1, 1, 11, 1, tzinfo=UTC),
        source="git",
    )

    event_repo = Mock(spec=EventRepository)
    evidence_repo = Mock(spec=EvidenceRepository)

    event_repo.list_for_project.return_value = [event_2, event_1]
    evidence_repo.get_by_reference.side_effect = [
        evidence_2,
        evidence_1,
    ]

    history = reconstruct_history(
        project=project,
        event_repository=event_repo,
        evidence_repository=evidence_repo,
    )

    assert history.project_id == project.id

    assert history.entries[0].event == event_1
    assert history.entries[0].evidence == evidence_1

    assert history.entries[1].event == event_2
    assert history.entries[1].evidence == evidence_2


def test_reconstruct_history_handles_missing_evidence(tmp_path):
    project_id = uuid4()

    project = Project(
        id=project_id,
        name="test-project",
        repository_path=tmp_path,
    )

    event_1 = Event(
        project_id=project_id,
        type="git_commit",
        timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        summary="Add initial implementation",
        source="git",
        source_reference="commit-1",
    )

    event_2 = Event(
        project_id=project_id,
        type="git_commit",
        timestamp=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        summary="Fix implementation",
        source="git",
        source_reference="commit-2",
    )

    evidence_1 = Evidence(
        project_id=project_id,
        type="git_diff",
        content="diff for commit 1",
        reference="commit-1",
        captured_at=datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
        source="git",
    )

    event_repo = Mock(spec=EventRepository)
    evidence_repo = Mock(spec=EvidenceRepository)

    event_repo.list_for_project.return_value = [event_1, event_2]
    evidence_repo.get_by_reference.side_effect = [evidence_1, None]

    with pytest.raises(HistoryReconstructionError) as exc_info:
        reconstruct_history(
            project=project,
            event_repository=event_repo,
            evidence_repository=evidence_repo,
        )

    assert "commit-2" in str(exc_info.value)


def test_reconstruct_history_handles_empty_project_case(tmp_path):
    project_id = uuid4()

    project = Project(
        id=project_id,
        name="test-project",
        repository_path=tmp_path,
    )

    event_repo = Mock(spec=EventRepository)
    evidence_repo = Mock(spec=EvidenceRepository)

    event_repo.list_for_project.return_value = []

    history = reconstruct_history(
        project=project,
        event_repository=event_repo,
        evidence_repository=evidence_repo,
    )

    evidence_repo.get_by_reference.assert_not_called()

    assert history.project_id == project.id
    assert history.entries == []
