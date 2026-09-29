"""
Provides filesystem operations for Quilchoom's local workspace.
"""

from pathlib import Path


def initialize_workspace(repository_root: Path) -> Path:
    workspace_dir = repository_root / ".quilchoom"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "documents").mkdir(parents=True, exist_ok=True)

    return workspace_dir
