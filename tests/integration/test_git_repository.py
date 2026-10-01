"""
Integration tests for Quilchoom's Git repository infrastructure.
"""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from quilchoom.infrastructure.git.repository import find_repository_root, inspect_commit


def test_find_repository_root_from_root():
    repo_root = find_repository_root()

    assert repo_root is not None
    assert isinstance(repo_root, Path)
    assert (repo_root / ".git").exists()


def test_find_repository_root_from_nested_directory():
    repo_root = find_repository_root()
    nested_path = repo_root / "src" if repo_root else None

    found_root = find_repository_root(nested_path)

    assert repo_root is not None
    assert found_root == repo_root


def test_find_repository_root_outside_git_repository(tmp_path):
    repo_root = find_repository_root(tmp_path)
    assert repo_root is None


def test_inspect_commit(tmp_path):
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    (tmp_path / "README.md").touch()
    (tmp_path / "src").mkdir()

    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    sha = result.stdout.strip()

    commit = inspect_commit(repository_path=tmp_path, commit_sha=sha)

    assert commit.sha == sha
    assert isinstance(commit.timestamp, datetime)
    assert commit.timestamp.tzinfo is UTC
    assert commit.message == "Initial commit"
    assert commit.diff != ""
