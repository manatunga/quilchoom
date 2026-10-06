"""
Integrated tests for Quilchoom's SQLite engine.
"""

from sqlalchemy import Engine, inspect

from quilchoom.infrastructure.database.connection import (
    create_database_engine,
    initialize_database,
)


def test_create_database_engine_success(tmp_path):
    db_path = tmp_path / "quilchoom.db"
    db_path.touch()

    db_engine = create_database_engine(db_path)

    assert db_path.exists()
    assert isinstance(db_engine, Engine)

    with db_engine.connect() as conn:
        assert conn.closed is False


def test_initialize_database_success(tmp_path):
    db_path = tmp_path / "quilchoom.db"

    db_engine = create_database_engine(db_path)
    initialize_database(db_engine)

    inspector = inspect(db_engine)
    tables = inspector.get_table_names()

    assert "projects" in tables
