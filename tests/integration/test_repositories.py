"""
Integration tests for Quilchoom's database repositories.
"""

from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base, ProjectModel
from quilchoom.infrastructure.database.repositories import ProjectRepository


def test_save_success(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    repository = ProjectRepository(db_engine)
    repository.save(project)

    with Session(db_engine) as session:
        model = session.scalars(
            select(ProjectModel).where(ProjectModel.id == str(project.id))
        ).first()

        assert model is not None

        db_values = {
            col.name: getattr(model, col.name) for col in ProjectModel.__table__.columns
        }
        domain_values = project.model_dump()
        domain_values["id"] = str(domain_values["id"])
        domain_values["repository_path"] = str(domain_values["repository_path"])

        assert db_values == domain_values


def test_get_by_id_on_existing_project(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    repository = ProjectRepository(db_engine)
    repository.save(project)

    retrieved = repository.get_by_id(project.id)

    assert retrieved == project


def test_get_by_id_on_non_existent_project():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    repository = ProjectRepository(db_engine)

    retrieved = repository.get_by_id(uuid4())

    assert retrieved is None


def test_get_by_repository_path_on_existing_project(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    repository = ProjectRepository(db_engine)
    repository.save(project)

    retrieved = repository.get_by_repository_path(project.repository_path)

    assert retrieved == project


def test_get_by_repository_path_on_unknown_path(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    repository = ProjectRepository(db_engine)

    retrieved = repository.get_by_repository_path(tmp_path)

    assert retrieved is None
