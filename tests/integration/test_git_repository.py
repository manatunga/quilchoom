"""
Integration tests for Quilchoom's Git repository infrastructure.
"""

from pathlib import Path

from quilchoom.infrastructure.git.repository import find_repository_root


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
