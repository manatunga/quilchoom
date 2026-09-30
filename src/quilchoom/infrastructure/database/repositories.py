"""
Provides persistence operations for Quilchoom's domain objects.
"""

from datetime import UTC
from pathlib import Path
from uuid import UUID

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from quilchoom.domain.event import Event
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import EventModel, ProjectModel


class ProjectRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: ProjectModel) -> Project:
        return Project(
            id=UUID(model.id),
            name=model.name,
            repository_path=Path(model.repository_path),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def save(self, project: Project) -> None:
        with Session(self.engine) as session:
            project_model = ProjectModel(
                id=str(project.id),
                name=project.name,
                repository_path=str(project.repository_path),
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            session.add(project_model)
            session.commit()

    def get_by_id(self, project_id: UUID) -> Project | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(ProjectModel).where(ProjectModel.id == str(project_id))
            ).first()

            if model is None:
                return None

            project = self._to_domain(model)

            return project

    def get_by_repository_path(self, repository_path: Path) -> Project | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(ProjectModel).where(
                    ProjectModel.repository_path == str(repository_path)
                )
            ).first()

            if model is None:
                return None

            project = self._to_domain(model)

            return project


class EventRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: EventModel) -> Event:
        return Event(
            id=UUID(model.id),
            project_id=UUID(model.project_id),
            type=model.type,
            timestamp=model.timestamp.replace(tzinfo=UTC),
            summary=model.summary,
            source=model.source,
            source_reference=model.source_reference,
            metadata=model.event_metadata,
        )

    def save(self, event: Event) -> None:
        with Session(self.engine) as session:
            event_model = EventModel(
                id=str(event.id),
                project_id=str(event.project_id),
                type=event.type,
                timestamp=event.timestamp.replace(tzinfo=None),
                summary=event.summary,
                source=event.source,
                source_reference=event.source_reference,
                event_metadata=event.metadata,
            )
            session.add(event_model)
            session.commit()

    def get_by_id(self, event_id: UUID) -> Event | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(EventModel).where(EventModel.id == str(event_id))
            ).first()

            if model is None:
                return None

            event = self._to_domain(model)

            return event

    def list_for_project(self, project_id: UUID) -> list[Event]:
        with Session(self.engine) as session:
            models = session.scalars(
                select(EventModel)
                .where(EventModel.project_id == str(project_id))
                .order_by(EventModel.timestamp.asc())
            ).all()

            events = [self._to_domain(model) for model in models]

            return events
