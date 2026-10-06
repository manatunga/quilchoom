"""
Integration tests for Quilchoom's database migrations.
"""

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from quilchoom.infrastructure.database.connection import initialize_database
from quilchoom.infrastructure.database.errors import DatabaseMigrationError
from quilchoom.infrastructure.database.migrations import upgrade_database


def test_upgrade_creates_projects_table(tmp_path):
    db_path = tmp_path / "quilchoom.db"
    upgrade_database(db_path)

    db_engine = create_engine(f"sqlite:///{db_path}")

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "projects" in tables
    assert "alembic_version" in tables

    with db_engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()

        assert revision == "3382e88e4db2"


def test_upgrade_database_stamps_compatible_legacy_database(tmp_path):
    db_path = tmp_path / "quilchoom.db"

    db_engine = create_engine(f"sqlite:///{db_path}")
    initialize_database(db_engine)

    upgrade_database(db_path)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "projects" in tables
    assert "alembic_version" in tables

    with db_engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()

        assert revision == "3382e88e4db2"


def test_upgrade_database_rejects_incompatible_legacy_database(tmp_path):
    db_path = tmp_path / "quilchoom.db"

    db_engine = create_engine(f"sqlite:///{db_path}")

    with db_engine.begin() as connection:
        connection.execute(
            text("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
                """)
        )

    with pytest.raises(DatabaseMigrationError):
        upgrade_database(db_path)


def test_upgrade_database_creates_events_table(tmp_path):
    database_path = tmp_path / "quilchoom.db"

    upgrade_database(database_path)

    engine = create_engine(f"sqlite:///{database_path}")

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "projects" in tables
        assert "events" in tables

        columns = inspector.get_columns("events")
        column_names = [column["name"] for column in columns]

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

        foreign_keys = inspector.get_foreign_keys("events")
        project_foreign_key = next(
            fk for fk in foreign_keys if fk["constrained_columns"] == ["project_id"]
        )

        assert project_foreign_key["referred_table"] == "projects"
        assert project_foreign_key["referred_columns"] == ["id"]

        indexes = inspector.get_indexes("events")
        event_index = next(
            index
            for index in indexes
            if index["name"] == "ix_events_project_id_timestamp"
        )

        assert event_index["column_names"] == ["project_id", "timestamp"]

        constraints = inspect(engine).get_unique_constraints("events")

        assert any(
            constraint["name"] == "uq_events_project_source_reference"
            for constraint in constraints
        )

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert revision == "3382e88e4db2"

    finally:
        engine.dispose()


def test_upgrade_database_creates_evidence_table(tmp_path):
    database_path = tmp_path / "quilchoom.db"

    upgrade_database(database_path)

    engine = create_engine(f"sqlite:///{database_path}")

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "projects" in tables
        assert "events" in tables
        assert "evidence" in tables

        columns = inspector.get_columns("evidence")
        column_names = [column["name"] for column in columns]

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

        foreign_keys = inspector.get_foreign_keys("evidence")
        project_foreign_key = next(
            fk for fk in foreign_keys if fk["constrained_columns"] == ["project_id"]
        )

        assert project_foreign_key["referred_table"] == "projects"
        assert project_foreign_key["referred_columns"] == ["id"]

        indexes = inspector.get_indexes("evidence")
        event_index = next(
            index
            for index in indexes
            if index["name"] == "ix_evidence_project_id_captured_at"
        )

        assert event_index["column_names"] == ["project_id", "captured_at"]

        constraints = inspect(engine).get_unique_constraints("evidence")

        assert any(
            constraint["name"] == "uq_evidence_project_source_reference"
            for constraint in constraints
        )

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert revision == "3382e88e4db2"

    finally:
        engine.dispose()


def test_upgrade_database_creates_knowledge_claim_tables(tmp_path):
    database_path = tmp_path / "quilchoom.db"

    upgrade_database(database_path)

    engine = create_engine(f"sqlite:///{database_path}")

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "knowledge_claims" in tables
        assert "knowledge_claim_evidence" in tables

        claim_columns = inspector.get_columns("knowledge_claims")
        claim_column_names = [column["name"] for column in claim_columns]

        assert claim_column_names == [
            "id",
            "project_id",
            "statement",
            "confidence",
            "status",
            "basis",
        ]

        claim_primary_key = inspector.get_pk_constraint("knowledge_claims")
        assert claim_primary_key["constrained_columns"] == ["id"]

        claim_foreign_keys = inspector.get_foreign_keys("knowledge_claims")
        project_foreign_key = next(
            fk
            for fk in claim_foreign_keys
            if fk["constrained_columns"] == ["project_id"]
        )

        assert project_foreign_key["referred_table"] == "projects"
        assert project_foreign_key["referred_columns"] == ["id"]

        association_columns = inspector.get_columns("knowledge_claim_evidence")
        association_column_names = [column["name"] for column in association_columns]

        assert association_column_names == ["claim_id", "evidence_id"]

        association_primary_key = inspector.get_pk_constraint(
            "knowledge_claim_evidence"
        )
        assert association_primary_key["constrained_columns"] == [
            "claim_id",
            "evidence_id",
        ]

        association_foreign_keys = inspector.get_foreign_keys(
            "knowledge_claim_evidence"
        )

        claim_foreign_key = next(
            fk
            for fk in association_foreign_keys
            if fk["constrained_columns"] == ["claim_id"]
        )
        evidence_foreign_key = next(
            fk
            for fk in association_foreign_keys
            if fk["constrained_columns"] == ["evidence_id"]
        )

        assert claim_foreign_key["referred_table"] == "knowledge_claims"
        assert claim_foreign_key["referred_columns"] == ["id"]
        assert claim_foreign_key.get("options", {}).get("ondelete") == "CASCADE"

        assert evidence_foreign_key["referred_table"] == "evidence"
        assert evidence_foreign_key["referred_columns"] == ["id"]
        assert evidence_foreign_key.get("options", {}).get("ondelete") == "CASCADE"

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert revision == "3382e88e4db2"

    finally:
        engine.dispose()


def test_knowledge_claim_basis_migration_backfills_existing_claims(tmp_path):
    database_path = tmp_path / "quilchoom.db"
    database_url = f"sqlite:///{database_path.resolve()}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

    command.upgrade(config, "b746cacea516")

    engine = create_engine(database_url)

    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO projects (
                        id,
                        name,
                        repository_path,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        'project-1',
                        'Test Project',
                        '/tmp/test-project',
                        '2026-10-03 00:00:00',
                        '2026-10-03 00:00:00'
                    )
                """)
            )

            connection.execute(
                text("""
                    INSERT INTO knowledge_claims (
                        id,
                        project_id,
                        statement,
                        confidence,
                        status
                    )
                    VALUES (
                        'claim-1',
                        'project-1',
                        'Existing claim',
                        'high',
                        'active'
                    )
                """)
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            row = connection.execute(
                text("""
                    SELECT statement, basis
                    FROM knowledge_claims
                    WHERE id = 'claim-1'
                """)
            ).one()

        assert row.statement == "Existing claim"
        assert row.basis == "observation"

    finally:
        engine.dispose()


def test_upgrade_database_creates_corrections_table(tmp_path):
    database_path = tmp_path / "quilchoom.db"

    upgrade_database(database_path)

    engine = create_engine(f"sqlite:///{database_path}")

    try:
        inspector = inspect(engine)

        assert "corrections" in inspector.get_table_names()

        columns = {
            column["name"]: column for column in inspector.get_columns("corrections")
        }

        assert set(columns) == {
            "id",
            "project_id",
            "target_claim_id",
            "reason",
            "replacement_claim_id",
            "created_at",
        }

        assert columns["id"]["nullable"] is False
        assert columns["project_id"]["nullable"] is False
        assert columns["target_claim_id"]["nullable"] is False
        assert columns["reason"]["nullable"] is False
        assert columns["replacement_claim_id"]["nullable"] is True
        assert columns["created_at"]["nullable"] is False

        foreign_keys = inspector.get_foreign_keys("corrections")

        project_fk = next(
            fk for fk in foreign_keys if fk["constrained_columns"] == ["project_id"]
        )
        target_claim_fk = next(
            fk
            for fk in foreign_keys
            if fk["constrained_columns"] == ["target_claim_id"]
        )
        replacement_claim_fk = next(
            fk
            for fk in foreign_keys
            if fk["constrained_columns"] == ["replacement_claim_id"]
        )

        assert project_fk["referred_table"] == "projects"
        assert project_fk["referred_columns"] == ["id"]

        assert target_claim_fk["referred_table"] == "knowledge_claims"
        assert target_claim_fk["referred_columns"] == ["id"]

        assert replacement_claim_fk["referred_table"] == "knowledge_claims"
        assert replacement_claim_fk["referred_columns"] == ["id"]

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert revision == "3382e88e4db2"

    finally:
        engine.dispose()


def test_upgrade_database_creates_document_tables(tmp_path):
    database_path = tmp_path / "quilchoom.db"

    upgrade_database(database_path)

    engine = create_engine(f"sqlite:///{database_path}")

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "documents" in tables
        assert "document_versions" in tables
        assert "document_version_claims" in tables

        document_columns = {
            column["name"]: column for column in inspector.get_columns("documents")
        }

        assert set(document_columns) == {
            "id",
            "project_id",
            "key",
            "kind",
            "created_at",
        }

        assert document_columns["id"]["nullable"] is False
        assert document_columns["project_id"]["nullable"] is False
        assert document_columns["key"]["nullable"] is False
        assert document_columns["kind"]["nullable"] is False
        assert document_columns["created_at"]["nullable"] is False

        document_foreign_keys = inspector.get_foreign_keys("documents")
        project_fk = next(
            fk
            for fk in document_foreign_keys
            if fk["constrained_columns"] == ["project_id"]
        )

        assert project_fk["referred_table"] == "projects"
        assert project_fk["referred_columns"] == ["id"]

        document_constraints = inspector.get_unique_constraints("documents")
        project_key_constraint = next(
            constraint
            for constraint in document_constraints
            if constraint["name"] == "uq_documents_project_key"
        )

        assert project_key_constraint["column_names"] == ["project_id", "key"]

        version_columns = {
            column["name"]: column
            for column in inspector.get_columns("document_versions")
        }

        assert set(version_columns) == {
            "id",
            "document_id",
            "version_number",
            "content",
            "origin",
            "created_at",
        }

        assert version_columns["id"]["nullable"] is False
        assert version_columns["document_id"]["nullable"] is False
        assert version_columns["version_number"]["nullable"] is False
        assert version_columns["content"]["nullable"] is False
        assert version_columns["origin"]["nullable"] is False
        assert version_columns["created_at"]["nullable"] is False

        version_foreign_keys = inspector.get_foreign_keys("document_versions")
        document_fk = next(
            fk
            for fk in version_foreign_keys
            if fk["constrained_columns"] == ["document_id"]
        )

        assert document_fk["referred_table"] == "documents"
        assert document_fk["referred_columns"] == ["id"]

        version_constraints = inspector.get_unique_constraints("document_versions")
        version_number_constraint = next(
            constraint
            for constraint in version_constraints
            if constraint["name"] == "uq_document_versions_document_version_number"
        )

        assert version_number_constraint["column_names"] == [
            "document_id",
            "version_number",
        ]

        association_columns = inspector.get_columns("document_version_claims")
        association_column_names = [column["name"] for column in association_columns]

        assert association_column_names == [
            "document_version_id",
            "claim_id",
        ]

        association_primary_key = inspector.get_pk_constraint("document_version_claims")

        assert set(association_primary_key["constrained_columns"]) == {
            "document_version_id",
            "claim_id",
        }

        association_foreign_keys = inspector.get_foreign_keys("document_version_claims")

        version_fk = next(
            fk
            for fk in association_foreign_keys
            if fk["constrained_columns"] == ["document_version_id"]
        )
        claim_fk = next(
            fk
            for fk in association_foreign_keys
            if fk["constrained_columns"] == ["claim_id"]
        )

        assert version_fk["referred_table"] == "document_versions"
        assert version_fk["referred_columns"] == ["id"]
        assert version_fk.get("options", {}).get("ondelete") == "CASCADE"

        assert claim_fk["referred_table"] == "knowledge_claims"
        assert claim_fk["referred_columns"] == ["id"]
        assert claim_fk.get("options", {}).get("ondelete") == "CASCADE"

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert revision == "3382e88e4db2"

    finally:
        engine.dispose()
