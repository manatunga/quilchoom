"""
Unit tests for Quilchoom's project initialization use case.
"""

import subprocess

import pytest

from quilchoom.application.errors import ProjectInitializationError
from quilchoom.application.initialize_project import initialize_project
from quilchoom.domain.project import Project


def test_initialize_project_raise_project_initialization_error(tmp_path):
    with pytest.raises(ProjectInitializationError):
        initialize_project(tmp_path)


def test_initialize_project_success(tmp_path):
    repo_root = tmp_path / "my_project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        check=True,
    )

    project = initialize_project(repo_root)

    assert isinstance(project, Project)
    assert project.repository_path == repo_root
    assert project.name == repo_root.name
    assert (repo_root / ".quilchoom").is_dir()
    assert (repo_root / ".quilchoom" / "documents").is_dir()
    assert (repo_root / ".quilchoom" / "quilchoom.db").is_file()


def test_initialize_project_idempotency(tmp_path):
    repo_root = tmp_path / "my_project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        check=True,
    )

    project_a = initialize_project(repo_root)
    project_b = initialize_project(repo_root)

    assert project_a.id == project_b.id
    assert project_a.created_at == project_b.created_at
