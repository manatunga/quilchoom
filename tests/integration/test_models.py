"""
Integration tests for Quilchoom's SQLAlchemy database models.
"""

from sqlalchemy import create_engine, inspect

from quilchoom.infrastructure.database.models import Base


def test_database_models_success():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "projects" in tables

    columns = inspector.get_columns("projects")
    column_names = [column["name"] for column in columns]

    pk_cols = inspector.get_pk_constraint("projects")["constrained_columns"]

    assert column_names == ["id", "name", "repository_path", "created_at", "updated_at"]
    assert pk_cols == ["id"]


def test_database_models_unique_repository_path_constraint():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    unique_constraints = inspector.get_unique_constraints("projects")
    unique_columns = [constraint["column_names"] for constraint in unique_constraints]

    assert ["repository_path"] in unique_columns
