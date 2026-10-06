"""
Unit tests for Quilchoom's apply-correction application workflow.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from quilchoom.application.apply_correction import apply_correction
from quilchoom.application.errors import (
    CorrectionProjectMismatchError,
    SelfReplacementError,
)
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.infrastructure.database.errors import KnowledgeClaimNotFoundError
from quilchoom.infrastructure.database.repositories import (
    CorrectionRepository,
    KnowledgeClaimRepository,
)


def test_apply_correction_with_replacement():
    project_id = uuid4()

    target_claim = KnowledgeClaim(
        project_id=project_id,
        statement="Original interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )
    replacement_claim = KnowledgeClaim(
        project_id=project_id,
        statement="Corrected interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    correction_repo = Mock(spec=CorrectionRepository)

    claim_repo.get_by_id.side_effect = [
        target_claim,
        replacement_claim,
    ]

    correction = apply_correction(
        project_id=project_id,
        target_claim_id=target_claim.id,
        reason="The original interpretation was incomplete.",
        replacement_claim_id=replacement_claim.id,
        claim_repository=claim_repo,
        correction_repository=correction_repo,
    )

    assert correction.project_id == project_id
    assert correction.target_claim_id == target_claim.id
    assert correction.reason == "The original interpretation was incomplete."
    assert correction.replacement_claim_id == replacement_claim.id

    correction_repo.save_with_claim_status_update.assert_called_once_with(
        correction=correction,
        status=ClaimStatus.CORRECTED,
    )


def test_apply_correction_without_replacement():
    project_id = uuid4()

    target_claim = KnowledgeClaim(
        project_id=project_id,
        statement="Unsupported interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    correction_repo = Mock(spec=CorrectionRepository)

    claim_repo.get_by_id.return_value = target_claim

    correction = apply_correction(
        project_id=project_id,
        target_claim_id=target_claim.id,
        reason="The interpretation is no longer supported.",
        claim_repository=claim_repo,
        correction_repository=correction_repo,
    )

    assert correction.replacement_claim_id is None

    correction_repo.save_with_claim_status_update.assert_called_once_with(
        correction=correction,
        status=ClaimStatus.INVALIDATED,
    )


def test_apply_correction_rejects_missing_target_claim():
    project_id = uuid4()
    target_claim_id = uuid4()

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    correction_repo = Mock(spec=CorrectionRepository)

    claim_repo.get_by_id.return_value = None

    with pytest.raises(KnowledgeClaimNotFoundError):
        apply_correction(
            project_id=project_id,
            target_claim_id=target_claim_id,
            reason="Reason for correction",
            claim_repository=claim_repo,
            correction_repository=correction_repo,
        )

    correction_repo.save_with_claim_status_update.assert_not_called()


def test_apply_correction_rejects_target_from_different_project():
    project_id = uuid4()

    target_claim = KnowledgeClaim(
        project_id=uuid4(),
        statement="Original interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    correction_repo = Mock(spec=CorrectionRepository)

    claim_repo.get_by_id.return_value = target_claim

    with pytest.raises(CorrectionProjectMismatchError):
        apply_correction(
            project_id=project_id,
            target_claim_id=target_claim.id,
            reason="Reason for correction",
            claim_repository=claim_repo,
            correction_repository=correction_repo,
        )

    correction_repo.save_with_claim_status_update.assert_not_called()


def test_apply_correction_rejects_missing_replacement_claim():
    project_id = uuid4()

    target_claim = KnowledgeClaim(
        project_id=project_id,
        statement="Original interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )
    replacement_claim_id = uuid4()

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    correction_repo = Mock(spec=CorrectionRepository)

    claim_repo.get_by_id.side_effect = [
        target_claim,
        None,
    ]

    with pytest.raises(KnowledgeClaimNotFoundError):
        apply_correction(
            project_id=project_id,
            target_claim_id=target_claim.id,
            reason="Reason for correction",
            replacement_claim_id=replacement_claim_id,
            claim_repository=claim_repo,
            correction_repository=correction_repo,
        )

    correction_repo.save_with_claim_status_update.assert_not_called()


def test_apply_correction_rejects_replacement_from_different_project():
    project_id = uuid4()

    target_claim = KnowledgeClaim(
        project_id=project_id,
        statement="Original interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )
    replacement_claim = KnowledgeClaim(
        project_id=uuid4(),
        statement="Replacement interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    correction_repo = Mock(spec=CorrectionRepository)

    claim_repo.get_by_id.side_effect = [
        target_claim,
        replacement_claim,
    ]

    with pytest.raises(CorrectionProjectMismatchError):
        apply_correction(
            project_id=project_id,
            target_claim_id=target_claim.id,
            reason="Reason for correction",
            replacement_claim_id=replacement_claim.id,
            claim_repository=claim_repo,
            correction_repository=correction_repo,
        )

    correction_repo.save_with_claim_status_update.assert_not_called()


def test_apply_correction_rejects_self_replacement():
    project_id = uuid4()

    target_claim = KnowledgeClaim(
        project_id=project_id,
        statement="Original interpretation",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    correction_repo = Mock(spec=CorrectionRepository)

    claim_repo.get_by_id.return_value = target_claim

    with pytest.raises(SelfReplacementError):
        apply_correction(
            project_id=project_id,
            target_claim_id=target_claim.id,
            reason="Reason for correction",
            replacement_claim_id=target_claim.id,
            claim_repository=claim_repo,
            correction_repository=correction_repo,
        )

    claim_repo.get_by_id.assert_called_once_with(target_claim.id)
    correction_repo.save_with_claim_status_update.assert_not_called()
