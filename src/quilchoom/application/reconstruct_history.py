"""
Reconstructs a project's development history from its events and evidence.
"""

from quilchoom.application.errors import HistoryReconstructionError
from quilchoom.domain.history import DevelopmentHistory, HistoryEntry
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    EvidenceRepository,
)


def reconstruct_history(
    project: Project,
    event_repository: EventRepository,
    evidence_repository: EvidenceRepository,
) -> DevelopmentHistory:
    events = event_repository.list_for_project(project_id=project.id)
    evidence = [
        evidence_repository.get_by_reference(
            project_id=project.id, source=event.source, reference=event.source_reference
        )
        for event in events
    ]

    entries = []
    for event, ev in zip(events, evidence):
        if ev is None:
            raise HistoryReconstructionError(
                f"Missing evidence for event: {event.source_reference}"
            )

        entries.append(
            HistoryEntry(
                event=event,
                evidence=ev,
            )
        )
    entries.sort(key=lambda entry: entry.event.timestamp)

    history = DevelopmentHistory(
        project_id=project.id,
        entries=entries,
    )

    return history
