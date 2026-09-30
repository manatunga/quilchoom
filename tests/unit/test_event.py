"""
Unit tests for Quilchoom's Event domain object.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.event import Event


def test_event_init_defaults():
    project_id = uuid4()
    timestamp = datetime.now(UTC)

    event = Event(
        project_id=project_id,
        type="git_commit",
        timestamp=timestamp,
        summary="Added alembic migration infrastructure",
        source="git",
        source_reference="a1b2c3d",
    )

    assert bool(event.id) is True
    assert event.project_id == project_id
    assert event.type == "git_commit"
    assert event.timestamp == timestamp
    assert event.summary == "Added alembic migration infrastructure"
    assert event.source == "git"
    assert event.source_reference == "a1b2c3d"
    assert event.metadata is None


def test_event_init_creates_unique_ids():
    event1 = Event(
        project_id=uuid4(),
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Added alembic migration infrastructure",
        source="git",
        source_reference="a1b2c3d",
    )
    event2 = Event(
        project_id=uuid4(),
        type="test_failed",
        timestamp=datetime.now(UTC),
        summary="Failed alembic migration integration test",
        source="test",
        source_reference="abc123",
    )

    assert event1.id != event2.id


def test_event_id_is_uuid():
    event = Event(
        project_id=uuid4(),
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Added alembic migration infrastructure",
        source="git",
        source_reference="a1b2c3d",
    )
    assert isinstance(event.id, UUID)


def test_event_required_parameters():
    with pytest.raises(ValidationError) as exc_info:
        Event()  # type: ignore

    errors = exc_info.value.errors()
    missing_fields = [err["loc"][0] for err in errors if err["type"] == "missing"]

    assert set(missing_fields) == {
        "project_id",
        "type",
        "timestamp",
        "summary",
        "source",
        "source_reference",
    }


def test_event_accepts_metadata():
    metadata = {
        "commit_hash": "abc123",
        "files_changed": 3,
    }

    event = Event(
        project_id=uuid4(),
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Added Alembic migration infrastructure",
        source="git",
        source_reference="abc123",
        metadata=metadata,
    )

    assert event.metadata == metadata
