"""
Unit tests for atomic document content export.
"""

from pathlib import Path

import pytest

from quilchoom.infrastructure.filesystem.export import export_document_content


def test_export_document_content_writes_new_file(tmp_path):
    destination = tmp_path / "README.md"

    export_document_content(
        destination=destination,
        content="# Quilchoom\n",
    )

    assert destination.read_text() == "# Quilchoom\n"


def test_export_document_content_replaces_existing_file(tmp_path):
    destination = tmp_path / "README.md"
    destination.write_text("# Old README\n")

    export_document_content(
        destination=destination,
        content="# New README\n",
    )

    assert destination.read_text() == "# New README\n"


def test_export_document_content_cleans_up_after_failed_replace(
    tmp_path,
    monkeypatch,
):
    destination = tmp_path / "README.md"

    files_before = set(tmp_path.iterdir())

    def failing_replace(self: Path, target: Path) -> Path:
        raise PermissionError("replacement failed")

    monkeypatch.setattr(Path, "replace", failing_replace)

    with pytest.raises(PermissionError, match="replacement failed"):
        export_document_content(
            destination=destination,
            content="# Quilchoom\n",
        )

    files_after = set(tmp_path.iterdir())

    assert files_after == files_before
    assert not destination.exists()
