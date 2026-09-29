"""
Provides Git repository discovery and inspection for Quilchoom.
"""

import subprocess
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
