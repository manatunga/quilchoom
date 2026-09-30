"""
Integration tests for Quilchoom's database migrations.
"""

import pytest
from sqlalchemy import create_engine, inspect, text

from quilchoom.infrastructure.database.connection import initialize_database
from quilchoom.infrastructure.database.errors import DatabaseMigrationError
from quilchoom.infrastructure.database.migrations import upgrade_database


def test_upgrade_database_success(tmp_path):
    db_path = tmp_path / "quilchoom.db"
    upgrade_database(db_path)

    db_engine = create_engine(f"sqlite:///{db_path}")

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "projects" in tables
    assert "alembic_version" in tables

    with db_engine.connect() as connection:
        result = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()

        assert result == "11da2eb1dbf1"


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
        result = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()

        assert result == "11da2eb1dbf1"


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

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        assert revision == "11da2eb1dbf1"

    finally:
        engine.dispose()
