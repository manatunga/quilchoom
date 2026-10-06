"""
Integration tests for project document version retrieval.
"""

import pytest
from sqlalchemy import create_engine

from quilchoom.application.errors import (
    DocumentUnavailableError,
    DocumentVersionUnavailableError,
)
from quilchoom.application.get_document_version import get_document_version
from quilchoom.domain.document import (
    Document,
    DocumentVersion,
    DocumentVersionOrigin,
)
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    ProjectRepository,
)


def test_get_document_version_returns_latest_version(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    document_repository = DocumentRepository(engine)
    document_repository.save(document)

    version_one = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# Version 1",
        origin=DocumentVersionOrigin.GENERATED,
    )
    version_two = DocumentVersion(
        document_id=document.id,
        version_number=2,
        content="# Version 2",
        origin=DocumentVersionOrigin.GENERATED,
    )

    version_repository = DocumentVersionRepository(engine)
    version_repository.save(version_one)
    version_repository.save(version_two)

    result = get_document_version(
        project=project,
        key="readme",
        version_number=None,
        document_repository=document_repository,
        version_repository=version_repository,
    )

    assert result == version_two


def test_get_document_version_returns_requested_version(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    document_repository = DocumentRepository(engine)
    document_repository.save(document)

    version_one = DocumentVersion(
        document_id=document.id,
        version_number=1,
        content="# Version 1",
        origin=DocumentVersionOrigin.GENERATED,
    )
    version_two = DocumentVersion(
        document_id=document.id,
        version_number=2,
        content="# Version 2",
        origin=DocumentVersionOrigin.GENERATED,
    )

    version_repository = DocumentVersionRepository(engine)
    version_repository.save(version_one)
    version_repository.save(version_two)

    result = get_document_version(
        project=project,
        key="readme",
        version_number=1,
        document_repository=document_repository,
        version_repository=version_repository,
    )

    assert result == version_one


def test_get_document_version_rejects_missing_document(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    with pytest.raises(DocumentUnavailableError):
        get_document_version(
            project=project,
            key="readme",
            version_number=None,
            document_repository=DocumentRepository(engine),
            version_repository=DocumentVersionRepository(engine),
        )


def test_get_document_version_rejects_missing_requested_version(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    project = Project(name="my_project", repository_path=tmp_path)
    ProjectRepository(engine).save(project)

    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    document_repository = DocumentRepository(engine)
    document_repository.save(document)

    with pytest.raises(DocumentVersionUnavailableError):
        get_document_version(
            project=project,
            key="readme",
            version_number=2,
            document_repository=document_repository,
            version_repository=DocumentVersionRepository(engine),
        )
