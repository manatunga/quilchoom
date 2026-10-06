"""
Provides shared helpers for Git-backed tests.
"""

import subprocess
from pathlib import Path


def initialize_git_repository(path: Path) -> None:
    """Initialize a Git repository with a repository-local test identity."""

    subprocess.run(
        ["git", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Quilchoom Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@quilchoom.local"],
        cwd=path,
        check=True,
        capture_output=True,
    )
