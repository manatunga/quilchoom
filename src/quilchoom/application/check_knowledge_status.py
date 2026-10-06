"""
Determines whether a project has captured evidence awaiting interpretation.
"""

from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    EvidenceRepository,
    InterpretationRunRepository,
)


def count_pending_evidence(
    project: Project,
    evidence_repository: EvidenceRepository,
    run_repository: InterpretationRunRepository,
) -> int:
    """Counts captured evidence that has not yet been interpreted."""

    evidence = evidence_repository.list_for_project(project.id)
    interpreted_ids = run_repository.list_interpreted_evidence_ids(project.id)

    pending_ids = {item.id for item in evidence if item.id not in interpreted_ids}

    return len(pending_ids)
