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
    assert (repo_root / ".quilchoom" / "config.toml").is_file()
    assert (repo_root / ".quilchoom" / ".gitignore").is_file()
    assert (repo_root / ".quilchoom" / "quilchoom.db").is_file()
    assert not (repo_root / ".quilchoom" / "documents").exists()


def test_initialize_project_idempotency(tmp_path):
    repo_root = tmp_path / "my_project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        check=True,
    )

    project_a = initialize_project(repo_root)

    config_path = repo_root / ".quilchoom" / "config.toml"
    modified_content = '[ai]\nprovider = "openai"\nmodel = "custom-model"\n'
    config_path.write_text(modified_content)

    project_b = initialize_project(repo_root)

    assert project_a.id == project_b.id
    assert project_a.created_at == project_b.created_at
    assert config_path.read_text() == modified_content


def test_initialize_project_preserves_existing_config_without_database(tmp_path):
    repo_root = tmp_path / "my_project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        check=True,
    )

    (repo_root / ".quilchoom").mkdir()
    config_path = repo_root / ".quilchoom" / "config.toml"
    config_content = '[ai]\nprovider = "openai"\nmodel = "custom-model"\n'
    config_path.write_text(config_content)

    project = initialize_project(repo_root)

    assert config_path.read_text() == config_content
    assert (repo_root / ".quilchoom" / "quilchoom.db").is_file()
    assert isinstance(project, Project)


def test_initialize_project_preserves_identity_after_repository_move(tmp_path):
    original_path = tmp_path / "original"
    original_path.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=original_path,
        check=True,
    )

    project_before_move = initialize_project(original_path)

    moved_path = tmp_path / "moved"
    original_path.rename(moved_path)
    project_after_move = initialize_project(moved_path)

    assert project_after_move.id == project_before_move.id
    assert project_after_move.created_at == project_before_move.created_at
    assert project_after_move.repository_path == moved_path
    assert not original_path.exists()
