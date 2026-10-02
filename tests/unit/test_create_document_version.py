"""
Unit tests for Quilchoom's create-document-version application workflow.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from quilchoom.application.create_document_version import create_document_version
from quilchoom.domain.document import (
    Document,
    DocumentVersion,
    DocumentVersionOrigin,
)
from quilchoom.infrastructure.database.errors import DocumentNotFoundError
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
)


def test_create_first_document_version():
    project_id = uuid4()

    document = Document(
        project_id=project_id,
        key="readme",
        kind="readme",
    )

    document_repo = Mock(spec=DocumentRepository)
    version_repo = Mock(spec=DocumentVersionRepository)

    document_repo.get_by_id.return_value = document
    version_repo.get_latest.return_value = None

    version = create_document_version(
        document_id=document.id,
        content="# My Project",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[],
        document_repository=document_repo,
        version_repository=version_repo,
    )

    assert version.document_id == document.id
    assert version.version_number == 1
    assert version.content == "# My Project"
    assert version.origin == DocumentVersionOrigin.GENERATED
    assert version.claim_ids == []

    version_repo.save.assert_called_once_with(version)


def test_create_document_version_increments_latest_version():
    project_id = uuid4()

    document = Document(
        project_id=project_id,
        key="readme",
        kind="readme",
    )
    latest_version = DocumentVersion(
        document_id=document.id,
        version_number=2,
        content="# Previous Version",
        origin=DocumentVersionOrigin.GENERATED,
    )

    document_repo = Mock(spec=DocumentRepository)
    version_repo = Mock(spec=DocumentVersionRepository)

    document_repo.get_by_id.return_value = document
    version_repo.get_latest.return_value = latest_version

    version = create_document_version(
        document_id=document.id,
        content="# New Version",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=[],
        document_repository=document_repo,
        version_repository=version_repo,
    )

    assert version.version_number == 3

    version_repo.save.assert_called_once_with(version)


def test_create_document_version_preserves_claim_provenance():
    project_id = uuid4()
    claim_ids = [uuid4(), uuid4()]

    document = Document(
        project_id=project_id,
        key="architecture",
        kind="architecture",
    )

    document_repo = Mock(spec=DocumentRepository)
    version_repo = Mock(spec=DocumentVersionRepository)

    document_repo.get_by_id.return_value = document
    version_repo.get_latest.return_value = None

    version = create_document_version(
        document_id=document.id,
        content="# Architecture",
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=claim_ids,
        document_repository=document_repo,
        version_repository=version_repo,
    )

    assert version.claim_ids == claim_ids

    version_repo.save.assert_called_once_with(version)


def test_create_document_version_rejects_missing_document():
    document_id = uuid4()

    document_repo = Mock(spec=DocumentRepository)
    version_repo = Mock(spec=DocumentVersionRepository)

    document_repo.get_by_id.return_value = None

    with pytest.raises(DocumentNotFoundError):
        create_document_version(
            document_id=document_id,
            content="# Missing Document",
            origin=DocumentVersionOrigin.GENERATED,
            claim_ids=[],
            document_repository=document_repo,
            version_repository=version_repo,
        )

    version_repo.get_latest.assert_not_called()
    version_repo.save.assert_not_called()
