"""
Provides persistence operations for Quilchoom's domain objects.
"""

from pathlib import Path
from uuid import UUID

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import ProjectModel


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
