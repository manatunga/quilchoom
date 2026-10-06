"""
Captures a Git commit as an Event and its supporting Evidence.
"""

from datetime import UTC, datetime
from pathlib import Path

from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    EvidenceRepository,
)
from quilchoom.infrastructure.git.repository import inspect_commit


def capture_commit(
    project: Project,
    repository_path: Path,
    commit_sha: str,
    event_repository: EventRepository,
    evidence_repository: EvidenceRepository,
) -> tuple[Event, Evidence]:
    commit = inspect_commit(repository_path, commit_sha)

    existing_event = event_repository.get_by_source_reference(
        project.id,
        "git",
        commit.sha,
    )

    existing_evidence = evidence_repository.get_by_reference(
        project.id,
        "git",
        commit.sha,
    )

    if existing_event is not None and existing_evidence is not None:
        return existing_event, existing_evidence

    event = existing_event or Event(
        project_id=project.id,
        type="git_commit",
        timestamp=commit.timestamp,
        summary=commit.message,
        source="git",
        source_reference=commit.sha,
    )
    evidence = existing_evidence or Evidence(
        project_id=project.id,
        type="git_diff",
        content=commit.diff,
        reference=commit.sha,
        captured_at=datetime.now(UTC),
        source="git",
    )

    if existing_event is None and existing_evidence is None:
        event_repository.save_with_evidence(event, evidence)

    elif existing_event is None:
        event_repository.save(event)

    elif existing_evidence is None:
        evidence_repository.save(evidence)

    return event, evidence
