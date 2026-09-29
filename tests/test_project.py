"""
Automated test suite for the project domain object.
"""

from uuid import UUID

import pytest
from pydantic import ValidationError

from quilchoom.domain.project import Project


def test_project_init(tmp_path):
    project = Project(name="my_project", repository_path=tmp_path)

    assert bool(project.id) is True
    assert project.name == "my_project"
    assert project.repository_path == tmp_path
    assert bool(project.created_at) is True
    assert bool(project.updated_at) is True


def test_project_init_creates_unique_ids(tmp_path):
    path1 = tmp_path / "dir1"
    path2 = tmp_path / "dir2"

    project1 = Project(name="project_1", repository_path=path1)
    project2 = Project(name="project_2", repository_path=path2)

    assert project1.id != project2.id


def test_project_id_is_uuid(tmp_path):
    project = Project(name="my_project", repository_path=tmp_path)
    assert isinstance(project.id, UUID)


def test_project_repository_path_validation():
    with pytest.raises(ValidationError):
        Project(name="my_project", repository_path=123)  # type: ignore
