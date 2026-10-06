"""
Provides filesystem operations for Quilchoom's local workspace.
"""

from pathlib import Path


def initialize_workspace(repository_root: Path) -> Path:
    workspace_dir = repository_root / ".quilchoom"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    gitignore_path = workspace_dir / ".gitignore"

    if not gitignore_path.is_file():
        gitignore_path.write_text("quilchoom.db\n")

    return workspace_dir


def find_workspace(repository_root: Path) -> Path | None:
    workspace = repository_root / ".quilchoom"

    if workspace.is_dir():
        return workspace

    return None
