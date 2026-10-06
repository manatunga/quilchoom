"""
Unit tests for Quilchoom's development history domain objects.
"""

from datetime import UTC, datetime
from uuid import uuid4

from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.history import DevelopmentHistory, HistoryEntry


def test_history_events_defaults():
    project_id = uuid4()

    event = Event(
        project_id=project_id,
        type="git_commit",
        timestamp=datetime(2026, 10, 1, 13, 3, 0, tzinfo=UTC),
        summary="Add history domain objects",
        source="git",
        source_reference="a1b2c3d",
    )
    evidence = Evidence(
        project_id=project_id,
        type="git_diff",
        content="diff --git",
        reference="a1b2c3d",
        captured_at=datetime(2026, 10, 1, 16, 1, tzinfo=UTC),
        source="git",
    )

    entry = HistoryEntry(event=event, evidence=evidence)

    assert entry.event == event
    assert entry.evidence == evidence


def test_development_history_contain_entries_and_preserves_order():
    project_id = uuid4()

    event_1 = Event(
        project_id=project_id,
        type="git_commit",
        timestamp=datetime(2026, 10, 1, 10, 3, 0, tzinfo=UTC),
        summary="Add history domain objects",
        source="git",
        source_reference="a1b2c3d",
    )
    evidence_1 = Evidence(
        project_id=project_id,
        type="git_diff",
        content="diff --git",
        reference="a1b2c3d",
        captured_at=datetime(2026, 10, 1, 11, 1, tzinfo=UTC),
        source="git",
    )

    entry_1 = HistoryEntry(event=event_1, evidence=evidence_1)

    event_2 = Event(
        project_id=project_id,
        type="git_commit",
        timestamp=datetime(2026, 10, 1, 11, 15, 0, tzinfo=UTC),
        summary="Add git capture",
        source="git",
        source_reference="bg3hjd8",
    )
    evidence_2 = Evidence(
        project_id=project_id,
        type="git_diff",
        content="diff --git",
        reference="bg3hjd8",
        captured_at=datetime(2026, 10, 1, 12, 29, tzinfo=UTC),
        source="git",
    )

    entry_2 = HistoryEntry(event=event_2, evidence=evidence_2)

    history = DevelopmentHistory(
        project_id=project_id,
        entries=[entry_1, entry_2],
    )

    assert history.project_id == project_id
    assert history.entries == [entry_1, entry_2]
    assert history.entries[0] == entry_1
    assert history.entries[1] == entry_2
