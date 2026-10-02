"""
Determines whether a document version relies on outdated knowledge claims.
"""

from quilchoom.domain.document import DocumentVersion
from quilchoom.domain.knowledge_claim import ClaimStatus
from quilchoom.infrastructure.database.errors import KnowledgeClaimNotFoundError
from quilchoom.infrastructure.database.repositories import KnowledgeClaimRepository


def is_document_version_stale(
    version: DocumentVersion,
    claim_repository: KnowledgeClaimRepository,
) -> bool:
    for claim_id in version.claim_ids:
        claim = claim_repository.get_by_id(claim_id)

        if claim is None:
            raise KnowledgeClaimNotFoundError(
                f"Knowledge claim referenced by document version not found: {claim_id}"
            )

        if claim.status != ClaimStatus.ACTIVE:
            return True

    return False
