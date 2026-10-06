"""
Integration tests for Quilchoom's Git repository infrastructure.
"""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from quilchoom.infrastructure.git.repository import (
    find_repository_root,
    inspect_commit,
    list_commit_shas,
)


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


def test_list_commit_shas_returns_commits_from_oldest_to_newest(tmp_path):
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    (tmp_path / "README.md").touch()

    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add reame"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    result_1 = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    sha_1 = result_1.stdout.strip()

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").touch()

    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "add src directory"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    result_2 = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    sha_2 = result_2.stdout.strip()

    (tmp_path / "README.md").write_text("My project")

    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "update readme"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    result_3 = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    sha_3 = result_3.stdout.strip()

    result = list_commit_shas(tmp_path)

    assert result == [sha_1, sha_2, sha_3]


def test_list_commit_shas_on_empty_repository(tmp_path):
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    result = list_commit_shas(tmp_path)

    assert result == []
