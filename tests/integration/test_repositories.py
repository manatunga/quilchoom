"""
Integration tests for Quilchoom's database repositories.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from quilchoom.domain.event import Event
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base, ProjectModel
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    ProjectRepository,
)


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


def test_save_and_get_event(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="my_project", repository_path=tmp_path)
    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
        summary="Added event persistence",
        source="git",
        source_reference="abc123",
    )
    event_repo = EventRepository(db_engine)
    event_repo.save(event)

    retrieved = event_repo.get_by_id(event.id)

    assert retrieved == event


def test_get_by_id_on_non_existent_event():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    repository = EventRepository(db_engine)

    retrieved = repository.get_by_id(uuid4())

    assert retrieved is None


def test_list_events_for_project(tmp_path):
    path1 = tmp_path / "project1"
    path2 = tmp_path / "project2"

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(name="project1", repository_path=path1)
    other_project = Project(name="project2", repository_path=path2)

    project_repo = ProjectRepository(db_engine)
    project_repo.save(project)
    project_repo.save(other_project)

    event_a = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 14, 0, tzinfo=UTC),
        summary="Added event persistence",
        source="git",
        source_reference="abc123",
    )
    event_b = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
        summary="Added evidence persistence",
        source="git",
        source_reference="a1b2c3",
    )
    event_c = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 13, 0, tzinfo=UTC),
        summary="Added alembic migration schema",
        source="git",
        source_reference="b3gh4s",
    )
    other_project_event = Event(
        project_id=other_project.id,
        type="git_commit",
        timestamp=datetime(2026, 9, 30, 11, 0, tzinfo=UTC),
        summary="Added event persistence",
        source="git",
        source_reference="akl343",
    )

    event_repo = EventRepository(db_engine)
    event_repo.save(event_a)
    event_repo.save(event_b)
    event_repo.save(event_c)
    event_repo.save(other_project_event)

    events = event_repo.list_for_project(project.id)

    assert events == [event_b, event_c, event_a]
