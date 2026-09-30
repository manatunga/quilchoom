"""
Integration tests for Quilchoom's SQLAlchemy database models.
"""

from sqlalchemy import JSON, create_engine, inspect

from quilchoom.infrastructure.database.models import Base


def test_project_model_success():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "projects" in tables

    columns = inspector.get_columns("projects")
    column_names = [column["name"] for column in columns]

    pk_cols = inspector.get_pk_constraint("projects")["constrained_columns"]

    assert column_names == [
        "id",
        "name",
        "repository_path",
        "created_at",
        "updated_at",
    ]
    assert pk_cols == ["id"]


def test_project_model_unique_repository_path_constraint():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    unique_constraints = inspector.get_unique_constraints("projects")
    unique_columns = [constraint["column_names"] for constraint in unique_constraints]

    assert ["repository_path"] in unique_columns


def test_event_model_defines_expected_schema():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "events" in tables

    columns = inspector.get_columns("events")
    column_names = [column["name"] for column in columns]

    pk_cols = inspector.get_pk_constraint("events")["constrained_columns"]

    assert column_names == [
        "id",
        "project_id",
        "type",
        "timestamp",
        "summary",
        "source",
        "source_reference",
        "metadata",
    ]
    assert pk_cols == ["id"]

    foreign_keys = inspector.get_foreign_keys("events")
    foreign_key = next(
        fk for fk in foreign_keys if fk["constrained_columns"] == ["project_id"]
    )

    assert foreign_key["referred_table"] == "projects"
    assert foreign_key["referred_columns"] == ["id"]

    project_id_column = next(
        column for column in columns if column["name"] == "project_id"
    )

    assert project_id_column["nullable"] is False

    composite_keys = inspector.get_indexes("events")
    composite_index = next(
        index
        for index in composite_keys
        if index["name"] == "ix_events_project_id_timestamp"
    )

    assert composite_index["column_names"] == ["project_id", "timestamp"]


def test_event_model_defines_metadata_as_json():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    columns = inspector.get_columns("events")
    col_type = next(col["type"] for col in columns if col["name"] == "metadata")

    assert isinstance(col_type, JSON)
