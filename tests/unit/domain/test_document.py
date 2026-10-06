"""
Unit tests for Quilchoom's Document and DocumentVersion domain objects.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.document import (
    Document,
    DocumentVersion,
    DocumentVersionOrigin,
)


def test_document_creation():
    project_id = uuid4()

    document = Document(
        project_id=project_id,
        key="readme",
        kind="readme",
    )

    assert document.project_id == project_id
    assert document.key == "readme"
    assert document.kind == "readme"
    assert document.created_at.tzinfo is not None


def test_document_generates_unique_ids():
    project_id = uuid4()

    document_1 = Document(
        project_id=project_id,
        key="readme",
        kind="readme",
    )
    document_2 = Document(
        project_id=project_id,
        key="architecture",
        kind="architecture",
    )

    assert document_1.id != document_2.id


@pytest.mark.parametrize(
    "missing_field",
    ["project_id", "key", "kind"],
)
def test_document_requires_fields(missing_field):
    data = {
        "project_id": uuid4(),
        "key": "readme",
        "kind": "readme",
    }
    del data[missing_field]

    with pytest.raises(ValidationError):
        Document(**data)


def test_document_version_creation():
    document_id = uuid4()

    version = DocumentVersion(
        document_id=document_id,
        version_number=1,
        content="# Quilchoom",
        origin=DocumentVersionOrigin.GENERATED,
    )

    assert version.document_id == document_id
    assert version.version_number == 1
    assert version.content == "# Quilchoom"
    assert version.origin == DocumentVersionOrigin.GENERATED
    assert version.claim_ids == []
    assert version.created_at.tzinfo is not None


def test_document_version_generates_unique_ids():
    document_id = uuid4()

    version_1 = DocumentVersion(
        document_id=document_id,
        version_number=1,
        content="# Version 1",
        origin=DocumentVersionOrigin.GENERATED,
    )
    version_2 = DocumentVersion(
        document_id=document_id,
        version_number=2,
        content="# Version 2",
        origin=DocumentVersionOrigin.GENERATED,
    )

    assert version_1.id != version_2.id


@pytest.mark.parametrize(
    "missing_field",
    ["document_id", "version_number", "content", "origin"],
)
def test_document_version_requires_fields(missing_field):
    data = {
        "document_id": uuid4(),
        "version_number": 1,
        "content": "# Quilchoom",
        "origin": DocumentVersionOrigin.GENERATED,
    }
    del data[missing_field]

    with pytest.raises(ValidationError):
        DocumentVersion(**data)


def test_document_version_origin_values():
    assert DocumentVersionOrigin.GENERATED.value == "generated"
    assert DocumentVersionOrigin.MANUAL.value == "manual"
    assert DocumentVersionOrigin.IMPORTED.value == "imported"


def test_document_version_handles_claim_provenance():
    claim_1 = uuid4()
    claim_2 = uuid4()

    version = DocumentVersion(
        document_id=uuid4(),
        version_number=1,
        content="# Quilchoom Version 1",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[claim_2, claim_1],
    )

    assert version.claim_ids[0] == claim_2
    assert version.claim_ids[1] == claim_1


@pytest.mark.parametrize("version_number", [0, -1])
def test_document_version_handles_invariant_version_number(version_number):
    with pytest.raises(ValidationError):
        DocumentVersion(
            document_id=uuid4(),
            version_number=version_number,
            content="Quilchoom generated content",
            origin=DocumentVersionOrigin.GENERATED,
            claim_ids=[uuid4()],
        )


def test_document_version_handles_invariant_content():
    with pytest.raises(ValidationError):
        DocumentVersion(
            document_id=uuid4(),
            version_number=2,
            content="",
            origin=DocumentVersionOrigin.MANUAL,
        )


def test_document_version_store_claim_lists_independently():
    version_1 = DocumentVersion(
        document_id=uuid4(),
        version_number=1,
        content="# Quilchoom markdown",
        origin=DocumentVersionOrigin.GENERATED,
    )
    version_2 = DocumentVersion(
        document_id=uuid4(),
        version_number=2,
        content="## New Section",
        origin=DocumentVersionOrigin.GENERATED,
    )

    version_1.claim_ids.append(uuid4())

    assert version_2.claim_ids == []
