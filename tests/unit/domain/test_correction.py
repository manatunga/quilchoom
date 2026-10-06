"""
Unit tests for Quilchoom's Correction domain object.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.correction import Correction


def test_correction_creation_without_replacement_claim():
    project_id = uuid4()
    target_claim_id = uuid4()

    correction = Correction(
        project_id=project_id,
        target_claim_id=target_claim_id,
        reason="Reason for correction",
    )

    assert isinstance(correction.id, UUID)
    assert correction.project_id == project_id
    assert correction.target_claim_id == target_claim_id
    assert correction.reason == "Reason for correction"
    assert correction.replacement_claim_id is None
    assert isinstance(correction.created_at, datetime)
    assert correction.created_at.tzinfo is not None


def test_correction_creation_with_replacement_claim():
    project_id = uuid4()
    target_claim_id = uuid4()
    replacement_claim_id = uuid4()

    correction = Correction(
        project_id=project_id,
        target_claim_id=target_claim_id,
        reason="Reason for correction",
        replacement_claim_id=replacement_claim_id,
    )

    assert correction.replacement_claim_id == replacement_claim_id


def test_correction_generates_unique_ids():
    project_id = uuid4()
    target_claim_id1 = uuid4()
    target_claim_id2 = uuid4()

    correction_1 = Correction(
        project_id=project_id,
        target_claim_id=target_claim_id1,
        reason="Reason for this correction",
    )
    correction_2 = Correction(
        project_id=project_id,
        target_claim_id=target_claim_id2,
        reason="Reason for that correction",
    )

    assert correction_1.id != correction_2.id


def test_correction_requires_valid_fields():
    with pytest.raises(ValidationError) as exc_info:
        Correction()  # type: ignore

    errors = exc_info.value.errors()
    missing_fields = [err["loc"][0] for err in errors if err["type"] == "missing"]

    assert set(missing_fields) == {
        "project_id",
        "target_claim_id",
        "reason",
    }
