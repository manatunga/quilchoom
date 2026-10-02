"""
Applies corrections to existing knowledge claims.
"""

from uuid import UUID

from quilchoom.application.errors import (
    CorrectionProjectMismatchError,
    SelfReplacementError,
)
from quilchoom.domain.correction import Correction
from quilchoom.domain.knowledge_claim import ClaimStatus
from quilchoom.infrastructure.database.errors import KnowledgeClaimNotFoundError
from quilchoom.infrastructure.database.repositories import (
    CorrectionRepository,
    KnowledgeClaimRepository,
)


def apply_correction(
    project_id: UUID,
    target_claim_id: UUID,
    reason: str,
    claim_repository: KnowledgeClaimRepository,
    correction_repository: CorrectionRepository,
    replacement_claim_id: UUID | None = None,
) -> Correction:
    target_claim = claim_repository.get_by_id(target_claim_id)

    if target_claim is None:
        raise KnowledgeClaimNotFoundError(
            f"Target knowledge claim not found: {target_claim_id}"
        )

    if target_claim.project_id != project_id:
        raise CorrectionProjectMismatchError(
            f"Target knowledge claim belongs to a different project: {target_claim.project_id}"
        )

    if replacement_claim_id is not None:
        if replacement_claim_id == target_claim_id:
            raise SelfReplacementError(
                f"Claim cannot be used as its own replacement: {replacement_claim_id}"
            )

        replacement_claim = claim_repository.get_by_id(replacement_claim_id)

        if replacement_claim is None:
            raise KnowledgeClaimNotFoundError(
                f"Replacement knowledge claim not found: {replacement_claim_id}"
            )

        if replacement_claim.project_id != project_id:
            raise CorrectionProjectMismatchError(
                f"Replacement knowledge claim belongs to a different project: {replacement_claim.project_id}"
            )

    if replacement_claim_id is not None:
        new_status = ClaimStatus.CORRECTED
    else:
        new_status = ClaimStatus.INVALIDATED

    correction = Correction(
        project_id=project_id,
        target_claim_id=target_claim.id,
        reason=reason,
        replacement_claim_id=replacement_claim_id,
    )

    correction_repository.save_with_claim_status_update(
        correction=correction,
        status=new_status,
    )

    return correction
