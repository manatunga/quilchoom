"""
Provides runtime loading for existing Quilchoom projects.
"""

from pathlib import Path

from pydantic import BaseModel

from quilchoom.application.errors import ProjectRuntimeError
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.connection import create_database_engine
from quilchoom.infrastructure.database.repositories import ProjectRepository
from quilchoom.infrastructure.filesystem.workspace import find_workspace
from quilchoom.infrastructure.git.repository import find_repository_root


class ProjectRuntime(BaseModel):
    """Represents the loaded runtime state of a Quilchoom project."""

    repository_root: Path
    workspace: Path
    database_path: Path
    project: Project


def load_project_runtime(
    repository_path: Path | None = None,
) -> ProjectRuntime:
    """Loads runtime state for an existing Quilchoom project."""

    repository_root = find_repository_root(repository_path)

    if repository_root is None:
        raise ProjectRuntimeError("Not inside a Git repository.")

    workspace = find_workspace(repository_root)

    if workspace is None:
        raise ProjectRuntimeError("Quilchoom is not initialized in this repository.")

    db_path = workspace / "quilchoom.db"

    if not db_path.is_file():
        raise ProjectRuntimeError("Quilchoom's local database is missing.")

    db_engine = create_database_engine(db_path)
    project_repository = ProjectRepository(db_engine)

    project = project_repository.get()

    if project is None:
        raise ProjectRuntimeError("Quilchoom's local project state is missing.")

    return ProjectRuntime(
        repository_root=repository_root,
        workspace=workspace,
        database_path=db_path,
        project=project,
    )
