"""
Unit tests for Quilchoom's KnowledgeClaim domain object and supporting enums.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.knowledge_claim import (
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)


def test_knowledge_claim_creation():
    project_id = uuid4()
    evidence_id = uuid4()

    claim = KnowledgeClaim(
        project_id=project_id,
        statement="Git capture was made idempotent",
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_id],
    )

    assert isinstance(claim.id, UUID)
    assert claim.project_id == project_id
    assert claim.statement == "Git capture was made idempotent"
    assert claim.confidence == ClaimConfidence.HIGH
    assert claim.status == ClaimStatus.ACTIVE
    assert claim.evidence_ids == [evidence_id]


def test_knowledge_claim_generates_unique_ids():
    project_id = uuid4()
    evidence_id1 = uuid4()
    evidence_id2 = uuid4()

    claim_1 = KnowledgeClaim(
        project_id=project_id,
        statement="Git capture was made idempotent",
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_id1],
    )
    claim_2 = KnowledgeClaim(
        project_id=project_id,
        statement="Git capture was made idempotent",
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_id2],
    )

    assert claim_1.id != claim_2.id


def test_knowledge_claim_requires_evidence():
    project_id = uuid4()

    with pytest.raises(ValidationError):
        KnowledgeClaim(
            project_id=project_id,
            statement="Git capture was made idempotent",
            confidence=ClaimConfidence.HIGH,
            status=ClaimStatus.ACTIVE,
            evidence_ids=[],
        )


def test_knowledge_claim_requires_valid_fields():
    project_id = uuid4()
    evidence_id = uuid4()

    with pytest.raises(ValidationError):
        KnowledgeClaim(
            project_id=project_id,
            statement=None,  # type: ignore
            confidence=ClaimConfidence.HIGH,
            status=ClaimStatus.ACTIVE,
            evidence_ids=[evidence_id],
        )

    with pytest.raises(ValidationError):
        KnowledgeClaim(
            project_id=None,  # type: ignore
            statement="Git capture has been made idempotent",
            confidence=ClaimConfidence.HIGH,
            status=ClaimStatus.ACTIVE,
            evidence_ids=[evidence_id],
        )

    with pytest.raises(ValidationError):
        KnowledgeClaim(
            project_id=project_id,
            statement="Git capture has been made idempotent",
            confidence=None,  # type: ignore
            status=ClaimStatus.ACTIVE,
            evidence_ids=[evidence_id],
        )

    with pytest.raises(ValidationError):
        KnowledgeClaim(
            project_id=project_id,
            statement="Git capture has been made idempotent",
            confidence=ClaimConfidence.HIGH,
            status=None,  # type: ignore
            evidence_ids=[evidence_id],
        )


def test_knowledge_claim_enum_values():
    assert ClaimConfidence.LOW.value == "low"
    assert ClaimConfidence.MEDIUM.value == "medium"
    assert ClaimConfidence.HIGH.value == "high"

    assert ClaimStatus.ACTIVE.value == "active"
    assert ClaimStatus.CORRECTED.value == "corrected"
    assert ClaimStatus.INVALIDATED.value == "invalidated"
