"""
Captures uncaptured Git commits for a Quilchoom project.
"""

from dataclasses import dataclass
from pathlib import Path

from quilchoom.application.capture_commit import capture_commit
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    EvidenceRepository,
)
from quilchoom.infrastructure.git.repository import list_commit_shas


@dataclass(frozen=True)
class CaptureResult:
    """Represents the result of capturing repository development activity."""

    discovered_commits: int
    captured_commits: int


def capture_repository(
    project: Project,
    repository_path: Path,
    event_repository: EventRepository,
    evidence_repository: EvidenceRepository,
) -> CaptureResult:
    commit_shas = list_commit_shas(repository_path)

    existing_evidence = evidence_repository.list_for_project(project.id)

    references = {
        evidence.reference for evidence in existing_evidence if evidence.source == "git"
    }

    uncaptured = [sha for sha in commit_shas if sha not in references]

    for sha in uncaptured:
        capture_commit(
            project=project,
            repository_path=repository_path,
            commit_sha=sha,
            event_repository=event_repository,
            evidence_repository=evidence_repository,
        )

    return CaptureResult(
        discovered_commits=len(commit_shas),
        captured_commits=len(uncaptured),
    )
