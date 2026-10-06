"""
Retrieves a requested version of a project document.
"""

from quilchoom.application.errors import (
    DocumentUnavailableError,
    DocumentVersionUnavailableError,
)
from quilchoom.domain.document import DocumentVersion
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
)


def get_document_version(
    project: Project,
    key: str,
    version_number: int | None,
    document_repository: DocumentRepository,
    version_repository: DocumentVersionRepository,
) -> DocumentVersion:
    """Retrieves the latest or requested version of a project document."""

    document = document_repository.get_by_key(project_id=project.id, key=key)

    if document is None:
        raise DocumentUnavailableError(f"Document not found: {key}")

    if version_number is None:
        version = version_repository.get_latest(document_id=document.id)

    else:
        version = version_repository.get_by_version_number(
            document_id=document.id, version_number=version_number
        )

    if version is None:
        if version_number is None:
            raise DocumentVersionUnavailableError("Latest document version not found")

        else:
            raise DocumentVersionUnavailableError(
                f"Document version not found: {version_number}"
            )

    return version
