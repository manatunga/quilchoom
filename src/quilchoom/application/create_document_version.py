"""
Creates new versions of existing documentation artifacts.
"""

from uuid import UUID

from quilchoom.domain.document import DocumentVersion, DocumentVersionOrigin
from quilchoom.infrastructure.database.errors import DocumentNotFoundError
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
)


def create_document_version(
    document_id: UUID,
    content: str,
    origin: DocumentVersionOrigin,
    claim_ids: list[UUID],
    document_repository: DocumentRepository,
    version_repository: DocumentVersionRepository,
) -> DocumentVersion:
    target_document = document_repository.get_by_id(document_id)

    if target_document is None:
        raise DocumentNotFoundError(f"Target document not found: {document_id}")

    latest_version = version_repository.get_latest(document_id)

    if latest_version is not None:
        version_number = latest_version.version_number + 1

    else:
        version_number = 1

    version = DocumentVersion(
        document_id=document_id,
        version_number=version_number,
        content=content,
        origin=origin,
        claim_ids=claim_ids,
    )
    version_repository.save(version)

    return version
