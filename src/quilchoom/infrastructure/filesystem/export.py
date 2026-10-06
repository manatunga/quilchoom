"""
Provides atomic filesystem export for Quilchoom document content.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile


def export_document_content(destination: Path, content: str) -> None:
    """Atomically writes document content to a filesystem destination."""

    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)

        temporary_path.replace(destination)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
