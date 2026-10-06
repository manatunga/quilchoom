"""
Integration tests for loading existing Quilchoom project runtime state.
"""

import subprocess

import pytest

from quilchoom.application.errors import ProjectRuntimeError
from quilchoom.application.initialize_project import initialize_project
from quilchoom.application.runtime import load_project_runtime
from quilchoom.infrastructure.database.migrations import upgrade_database


def test_load_project_runtime_success(tmp_path):
    repo_root = tmp_path / "my_project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )

    initialized_project = initialize_project(repo_root)
    runtime = load_project_runtime(repo_root)

    assert runtime.repository_root == repo_root
    assert runtime.workspace == repo_root / ".quilchoom"
    assert runtime.database_path == repo_root / ".quilchoom" / "quilchoom.db"
    assert runtime.project == initialized_project


def test_load_project_runtime_does_not_initialize_workspace(tmp_path):
    repo_root = tmp_path / "my_project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )

    with pytest.raises(ProjectRuntimeError):
        load_project_runtime(repo_root)

    assert not (repo_root / ".quilchoom").exists()


def test_load_project_runtime_rejects_missing_database(tmp_path):
    repo_root = tmp_path / "my_project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )

    (repo_root / ".quilchoom").mkdir()

    with pytest.raises(ProjectRuntimeError, match="local database is missing"):
        load_project_runtime(repo_root)

    assert not (repo_root / ".quilchoom" / "quilchoom.db").exists()


def test_load_project_runtime_rejects_missing_project_state(tmp_path):
    repo_root = tmp_path / "my_project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        check=True,
    )

    workspace = repo_root / ".quilchoom"
    workspace.mkdir()

    db_path = workspace / "quilchoom.db"
    upgrade_database(db_path)

    with pytest.raises(ProjectRuntimeError, match="local project state is missing"):
        load_project_runtime(repo_root)

    assert db_path.is_file()
