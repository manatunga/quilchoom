"""
Provides Git repository discovery and inspection for Quilchoom.
"""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


def find_repository_root(path: Path | None = None) -> Path | None:
    cwd = path if path is not None else Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        return Path(result.stdout.strip())

    except OSError:
        return None


@dataclass(frozen=True)
class GitCommit:
    sha: str
    timestamp: datetime
    message: str
    diff: str


def inspect_commit(repository_path: Path, commit_sha: str) -> GitCommit:
    delimiter = "%x00%x00%x00"

    git_format = f"%H{delimiter}%ct{delimiter}%B"

    result = subprocess.run(
        [
            "git",
            "show",
            f"--format={git_format}",
            "--patch",
            commit_sha,
        ],
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=True,
    )

    parts = result.stdout.split("\x00\x00\x00", 2)

    if len(parts) < 3:
        raise ValueError(f"Failed to parse git show output for commit {commit_sha}")

    sha = parts[0].strip()
    unix_timestamp = int(parts[1].strip())
    message_and_diff = parts[2]

    diff_marker = "\ndiff --git"

    if diff_marker in message_and_diff:
        message, diff = message_and_diff.split(diff_marker, 1)
        diff = f"diff --git{diff}"
    else:
        message = message_and_diff
        diff = ""

    commit_datetime = datetime.fromtimestamp(unix_timestamp, tz=UTC)

    return GitCommit(
        sha=sha,
        timestamp=commit_datetime,
        message=message.strip(),
        diff=diff.strip(),
    )


def list_commit_shas(repository_path: Path) -> list[str]:
    verify_result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=False,
    )

    if verify_result.returncode != 0:
        return []

    result = subprocess.run(
        ["git", "rev-list", "--reverse", "HEAD"],
        cwd=repository_path,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.splitlines()
