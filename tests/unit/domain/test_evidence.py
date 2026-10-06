"""
Unit tests for Quilchoom's Evidence domain object.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.evidence import Evidence


def test_evidence_defaults():
    project_id = uuid4()
    captured_at = datetime.now(UTC)

    evidence = Evidence(
        project_id=project_id,
        type="git_commit",
        captured_at=captured_at,
        source="git",
    )

    assert bool(evidence.id) is True
    assert evidence.project_id == project_id
    assert evidence.type == "git_commit"
    assert evidence.content is None
    assert evidence.reference is None
    assert evidence.captured_at == captured_at
    assert evidence.source == "git"
    assert evidence.metadata is None


def test_evidence_generates_uuid():
    evidence = Evidence(
        project_id=uuid4(),
        type="git_commit",
        captured_at=datetime.now(UTC),
        source="git",
    )

    assert isinstance(evidence.id, UUID)


def test_evidence_requires_required_fields():
    with pytest.raises(ValidationError) as exc_info:
        Evidence()  # type: ignore

    errors = exc_info.value.errors()
    missing_fields = [err["loc"][0] for err in errors if err["type"] == "missing"]

    assert set(missing_fields) == {
        "project_id",
        "type",
        "captured_at",
        "source",
    }


def test_evidence_accepts_metadata():
    metadata = {"commit_hash": "abc123", "files_changed": 3}

    evidence = Evidence(
        project_id=uuid4(),
        type="git_commit",
        captured_at=datetime.now(UTC),
        source="git",
        metadata=metadata,
    )

    assert evidence.metadata == metadata


def test_evidence_accepts_content():
    content = "Git diff"

    evidence = Evidence(
        project_id=uuid4(),
        type="git_commit",
        content=content,
        captured_at=datetime.now(UTC),
        source="git",
    )

    assert evidence.content == content


def test_evidence_accepts_reference():
    reference = "Git commit"

    evidence = Evidence(
        project_id=uuid4(),
        type="git_commit",
        reference=reference,
        captured_at=datetime.now(UTC),
        source="git",
    )

    assert evidence.reference == reference
