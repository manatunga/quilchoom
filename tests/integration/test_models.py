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


def test_knowledge_claim_model_defines_expected_schema():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "knowledge_claims" in tables

    columns = inspector.get_columns("knowledge_claims")
    column_names = [column["name"] for column in columns]

    assert column_names == [
        "id",
        "project_id",
        "statement",
        "basis",
        "confidence",
        "status",
    ]

    pk_cols = inspector.get_pk_constraint("knowledge_claims")["constrained_columns"]
    assert pk_cols == ["id"]

    foreign_keys = inspector.get_foreign_keys("knowledge_claims")
    project_fk = next(
        fk for fk in foreign_keys if fk["constrained_columns"] == ["project_id"]
    )

    assert project_fk["referred_table"] == "projects"
    assert project_fk["referred_columns"] == ["id"]


def test_knowledge_claim_model_defines_expected_nullability():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    columns = inspector.get_columns("knowledge_claims")
    nullability = {column["name"]: column["nullable"] for column in columns}

    assert nullability["id"] is False
    assert nullability["project_id"] is False
    assert nullability["statement"] is False
    assert nullability["confidence"] is False
    assert nullability["status"] is False


def test_knowledge_claim_evidence_defines_expected_schema():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)

    columns = inspector.get_columns("knowledge_claim_evidence")
    column_names = [column["name"] for column in columns]

    assert column_names == ["claim_id", "evidence_id"]

    pk_cols = inspector.get_pk_constraint("knowledge_claim_evidence")[
        "constrained_columns"
    ]
    assert set(pk_cols) == {"claim_id", "evidence_id"}

    foreign_keys = inspector.get_foreign_keys("knowledge_claim_evidence")
    referenced_tables = {
        fk["referred_table"]: fk["constrained_columns"] for fk in foreign_keys
    }

    assert referenced_tables == {
        "knowledge_claims": ["claim_id"],
        "evidence": ["evidence_id"],
    }


def test_correction_model_defines_expected_schema():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "corrections" in tables

    columns = inspector.get_columns("corrections")
    column_names = [column["name"] for column in columns]

    assert column_names == [
        "id",
        "project_id",
        "target_claim_id",
        "reason",
        "replacement_claim_id",
        "created_at",
    ]

    pk_cols = inspector.get_pk_constraint("corrections")["constrained_columns"]

    assert pk_cols == ["id"]

    foreign_keys = inspector.get_foreign_keys("corrections")

    project_foreign_key = next(
        fk for fk in foreign_keys if fk["constrained_columns"] == ["project_id"]
    )
    target_claim_foreign_key = next(
        fk for fk in foreign_keys if fk["constrained_columns"] == ["target_claim_id"]
    )
    replacement_claim_foreign_key = next(
        fk
        for fk in foreign_keys
        if fk["constrained_columns"] == ["replacement_claim_id"]
    )

    assert project_foreign_key["referred_table"] == "projects"
    assert project_foreign_key["referred_columns"] == ["id"]

    assert target_claim_foreign_key["referred_table"] == "knowledge_claims"
    assert target_claim_foreign_key["referred_columns"] == ["id"]

    assert replacement_claim_foreign_key["referred_table"] == "knowledge_claims"
    assert replacement_claim_foreign_key["referred_columns"] == ["id"]


def test_correction_model_defines_expected_nullability():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    columns = inspector.get_columns("corrections")
    nullability = {column["name"]: column["nullable"] for column in columns}

    assert nullability["id"] is False
    assert nullability["project_id"] is False
    assert nullability["target_claim_id"] is False
    assert nullability["reason"] is False
    assert nullability["replacement_claim_id"] is True
    assert nullability["created_at"] is False


def test_document_model_defines_expected_schema():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "documents" in tables

    columns = inspector.get_columns("documents")
    column_names = [column["name"] for column in columns]

    assert column_names == [
        "id",
        "project_id",
        "key",
        "kind",
        "created_at",
    ]

    pk_cols = inspector.get_pk_constraint("documents")["constrained_columns"]

    assert pk_cols == ["id"]

    foreign_keys = inspector.get_foreign_keys("documents")
    project_foreign_key = next(
        fk for fk in foreign_keys if fk["constrained_columns"] == ["project_id"]
    )

    assert project_foreign_key["referred_table"] == "projects"
    assert project_foreign_key["referred_columns"] == ["id"]


def test_document_model_defines_expected_nullability():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    columns = inspector.get_columns("documents")
    nullability = {column["name"]: column["nullable"] for column in columns}

    assert nullability["id"] is False
    assert nullability["project_id"] is False
    assert nullability["key"] is False
    assert nullability["kind"] is False
    assert nullability["created_at"] is False


def test_document_model_defines_project_key_uniqueness():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    constraints = inspector.get_unique_constraints("documents")

    constraint = next(
        constraint
        for constraint in constraints
        if constraint["name"] == "uq_documents_project_key"
    )

    assert constraint["column_names"] == ["project_id", "key"]


def test_document_version_model_defines_expected_schema():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "document_versions" in tables

    columns = inspector.get_columns("document_versions")
    column_names = [column["name"] for column in columns]

    assert column_names == [
        "id",
        "document_id",
        "version_number",
        "content",
        "origin",
        "created_at",
    ]

    pk_cols = inspector.get_pk_constraint("document_versions")["constrained_columns"]

    assert pk_cols == ["id"]

    foreign_keys = inspector.get_foreign_keys("document_versions")
    document_foreign_key = next(
        fk for fk in foreign_keys if fk["constrained_columns"] == ["document_id"]
    )

    assert document_foreign_key["referred_table"] == "documents"
    assert document_foreign_key["referred_columns"] == ["id"]


def test_document_version_model_defines_expected_nullability():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    columns = inspector.get_columns("document_versions")
    nullability = {column["name"]: column["nullable"] for column in columns}

    assert nullability["id"] is False
    assert nullability["document_id"] is False
    assert nullability["version_number"] is False
    assert nullability["content"] is False
    assert nullability["origin"] is False
    assert nullability["created_at"] is False


def test_document_version_defines_document_version_number_uniqueness():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)
    constraints = inspector.get_unique_constraints("document_versions")

    constraint = next(
        constraint
        for constraint in constraints
        if constraint["name"] == "uq_document_versions_document_version_number"
    )

    assert constraint["column_names"] == ["document_id", "version_number"]


def test_document_version_claims_defines_expected_schema():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    inspector = inspect(db_engine)

    columns = inspector.get_columns("document_version_claims")
    column_names = [column["name"] for column in columns]

    assert column_names == ["document_version_id", "claim_id"]

    pk_cols = inspector.get_pk_constraint("document_version_claims")[
        "constrained_columns"
    ]

    assert set(pk_cols) == {"document_version_id", "claim_id"}

    foreign_keys = inspector.get_foreign_keys("document_version_claims")
    referenced_tables = {
        fk["referred_table"]: fk["constrained_columns"] for fk in foreign_keys
    }

    assert referenced_tables == {
        "document_versions": ["document_version_id"],
        "knowledge_claims": ["claim_id"],
    }
