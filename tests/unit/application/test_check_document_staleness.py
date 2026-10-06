"""
Unit tests for Quilchoom's document-staleness application workflow.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from quilchoom.application.check_document_staleness import (
    is_document_version_stale,
)
from quilchoom.domain.document import DocumentVersion, DocumentVersionOrigin
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.infrastructure.database.errors import KnowledgeClaimNotFoundError
from quilchoom.infrastructure.database.repositories import KnowledgeClaimRepository


def test_document_version_is_not_stale_when_all_claims_are_active():
    project_id = uuid4()

    first_claim = KnowledgeClaim(
        project_id=project_id,
        statement="First active claim",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )
    second_claim = KnowledgeClaim(
        project_id=project_id,
        statement="Second active claim",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    version = DocumentVersion(
        document_id=uuid4(),
        version_number=1,
        content="# Documentation",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[first_claim.id, second_claim.id],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    claim_repo.get_by_id.side_effect = [
        first_claim,
        second_claim,
    ]

    assert is_document_version_stale(version, claim_repo) is False


def test_document_version_is_stale_when_claim_is_corrected():
    project_id = uuid4()

    claim = KnowledgeClaim(
        project_id=project_id,
        statement="Corrected claim",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.CORRECTED,
        evidence_ids=[uuid4()],
    )

    version = DocumentVersion(
        document_id=uuid4(),
        version_number=1,
        content="# Documentation",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim.id],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    claim_repo.get_by_id.return_value = claim

    assert is_document_version_stale(version, claim_repo) is True


def test_document_version_is_stale_when_claim_is_invalidated():
    project_id = uuid4()

    claim = KnowledgeClaim(
        project_id=project_id,
        statement="Invalidated claim",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.INVALIDATED,
        evidence_ids=[uuid4()],
    )

    version = DocumentVersion(
        document_id=uuid4(),
        version_number=1,
        content="# Documentation",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim.id],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    claim_repo.get_by_id.return_value = claim

    assert is_document_version_stale(version, claim_repo) is True


def test_document_version_staleness_rejects_missing_claim():
    claim_id = uuid4()

    version = DocumentVersion(
        document_id=uuid4(),
        version_number=1,
        content="# Documentation",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim_id],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)
    claim_repo.get_by_id.return_value = None

    with pytest.raises(KnowledgeClaimNotFoundError):
        is_document_version_stale(version, claim_repo)


def test_document_version_without_claims_is_not_stale():
    version = DocumentVersion(
        document_id=uuid4(),
        version_number=1,
        content="# Manual Documentation",
        origin=DocumentVersionOrigin.MANUAL,
        claim_ids=[],
    )

    claim_repo = Mock(spec=KnowledgeClaimRepository)

    assert is_document_version_stale(version, claim_repo) is False

    claim_repo.get_by_id.assert_not_called()
