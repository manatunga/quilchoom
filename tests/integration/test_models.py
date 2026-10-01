"""
Integration tests for Quilchoom's SQLAlchemy database models.
"""

from sqlalchemy import JSON, create_engine, inspect

from quilchoom.infrastructure.database.models import Base


def test_project_model_defines_expected_schema():
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

    constraints = inspect(db_engine).get_unique_constraints("events")

    assert any(
        constraint["name"] == "uq_events_project_source_reference"
        for constraint in constraints
    )


def test_event_model_defines_metadata_as_json():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    columns = inspector.get_columns("events")
    col_type = next(col["type"] for col in columns if col["name"] == "metadata")

    assert isinstance(col_type, JSON)


def test_evidence_model_defines_expected_schema():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "evidence" in tables

    columns = inspector.get_columns("evidence")
    column_names = [column["name"] for column in columns]

    pk_cols = inspector.get_pk_constraint("evidence")["constrained_columns"]

    assert column_names == [
        "id",
        "project_id",
        "type",
        "content",
        "reference",
        "captured_at",
        "source",
        "metadata",
    ]
    assert pk_cols == ["id"]

    foreign_keys = inspector.get_foreign_keys("evidence")
    foreign_key = next(
        fk for fk in foreign_keys if fk["constrained_columns"] == ["project_id"]
    )

    assert foreign_key["referred_table"] == "projects"
    assert foreign_key["referred_columns"] == ["id"]

    project_id_column = next(
        column for column in columns if column["name"] == "project_id"
    )

    assert project_id_column["nullable"] is False

    composite_keys = inspector.get_indexes("evidence")
    composite_index = next(
        index
        for index in composite_keys
        if index["name"] == "ix_evidence_project_id_captured_at"
    )

    assert composite_index["column_names"] == ["project_id", "captured_at"]

    constraints = inspect(db_engine).get_unique_constraints("evidence")

    assert any(
        constraint["name"] == "uq_evidence_project_source_reference"
        for constraint in constraints
    )


def test_evidence_model_defines_expected_nullability():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    columns = inspector.get_columns("evidence")
    nullability = {column["name"]: column["nullable"] for column in columns}

    assert nullability["content"] is True
    assert nullability["reference"] is True
    assert nullability["metadata"] is True

    assert nullability["type"] is False
    assert nullability["captured_at"] is False
    assert nullability["source"] is False


def test_evidence_model_defines_metadata_as_json():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    columns = inspector.get_columns("evidence")
    metadata_type = next(
        column["type"] for column in columns if column["name"] == "metadata"
    )

    assert isinstance(metadata_type, JSON)
