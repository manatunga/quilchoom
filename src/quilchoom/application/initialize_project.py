"""
Initializes a Quilchoom project from a Git repository.
"""

from pathlib import Path

from quilchoom.application.errors import ProjectInitializationError
from quilchoom.domain.project import Project
from quilchoom.infrastructure.config import write_default_config
from quilchoom.infrastructure.database.connection import create_database_engine
from quilchoom.infrastructure.database.migrations import upgrade_database
from quilchoom.infrastructure.database.repositories import ProjectRepository
from quilchoom.infrastructure.filesystem.workspace import initialize_workspace
from quilchoom.infrastructure.git.repository import find_repository_root


def initialize_project(repository_path: Path | None = None) -> Project:
    repo_root = find_repository_root(repository_path)

    if repo_root is None:
        raise ProjectInitializationError()

    workspace = initialize_workspace(repo_root)

    config_path = workspace / "config.toml"
    write_default_config(config_path)

    db_path = workspace / "quilchoom.db"
    upgrade_database(db_path)

    db_engine = create_database_engine(db_path)

    project_repository = ProjectRepository(db_engine)
    existing_project = project_repository.get()

    if existing_project is not None:
        if existing_project.repository_path == repo_root:
            return existing_project

        updated_project = project_repository.update_repository_path(
            existing_project.id,
            repo_root,
        )

        return updated_project

    project = Project(
        name=repo_root.name,
        repository_path=repo_root,
    )
    project_repository.save(project)

    return project
