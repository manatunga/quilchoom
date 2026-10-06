"""
Integration tests for Quilchoom's local workspace filesystem.
"""

from quilchoom.infrastructure.filesystem.workspace import (
    find_workspace,
    initialize_workspace,
)


def test_initialize_workspace_success(tmp_path):
    ws_dir = initialize_workspace(tmp_path)

    assert ws_dir == (tmp_path / ".quilchoom")
    assert ws_dir.is_dir()
    assert (ws_dir / ".gitignore").is_file()
    assert (ws_dir / ".gitignore").read_text() == "quilchoom.db\n"
    assert not (ws_dir / "documents").exists()


def test_initialize_workspace_is_idempotent(tmp_path):
    ws_dir1 = initialize_workspace(tmp_path)
    gitignore_content = (ws_dir1 / ".gitignore").read_text()

    ws_dir2 = initialize_workspace(tmp_path)

    assert ws_dir1 == ws_dir2
    assert ws_dir1.is_dir()
    assert ws_dir2.is_dir()
    assert (ws_dir2 / ".gitignore").read_text() == gitignore_content


def test_find_workspace_returns_existing_workspace(tmp_path):
    workspace = tmp_path / ".quilchoom"
    workspace.mkdir()

    found = find_workspace(tmp_path)

    assert found == workspace


def test_find_workspace_returns_none_when_workspace_missing(tmp_path):
    found = find_workspace(tmp_path)

    assert found is None
