"""
Integration tests for Quilchoom's local workspace filesystem.
"""

from quilchoom.infrastructure.filesystem.workspace import initialize_workspace


def test_initialize_workspace_success(tmp_path):
    ws_dir = initialize_workspace(tmp_path)

    assert ws_dir == (tmp_path / ".quilchoom")
    assert ws_dir.is_dir()
    assert (ws_dir / "documents").is_dir()


def test_initialize_workspace_is_idempotent(tmp_path):
    ws_dir1 = initialize_workspace(tmp_path)
    ws_dir2 = initialize_workspace(tmp_path)

    assert ws_dir1 == ws_dir2
    assert ws_dir1.is_dir()
    assert ws_dir2.is_dir()
