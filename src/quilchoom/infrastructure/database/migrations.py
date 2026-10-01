"""
Provides database schema migration operations for Quilchoom.
"""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import Inspector, create_engine, inspect

from alembic import command
from quilchoom.infrastructure.database.errors import DatabaseMigrationError


def upgrade_database(database_path: Path) -> None:
    """Upgrade a workspace database to the latest schema."""
    project_root = Path(__file__).resolve().parents[4]
    alembic_ini = project_root / "alembic.ini"

    config = Config(str(alembic_ini))

    database_url = f"sqlite:///{database_path.resolve()}"
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if not tables:
        command.upgrade(config, "head")
        return

    if "alembic_version" in tables:
        command.upgrade(config, "head")
        return

    if _has_compatible_legacy_schema(inspector):
        command.stamp(config, "head")
        return

    raise DatabaseMigrationError(
        "Existing Quilchoom database has an incompatible schema."
    )


def _has_compatible_legacy_schema(inspector: Inspector) -> bool:
    if "projects" not in inspector.get_table_names():
        return False

    columns = inspector.get_columns("projects")
    column_names = [column["name"] for column in columns]

    if column_names != [
        "id",
        "name",
        "repository_path",
        "created_at",
        "updated_at",
    ]:
        return False

    primary_key = inspector.get_pk_constraint("projects")

    if primary_key["constrained_columns"] != ["id"]:
        return False

    unique_constraints = inspector.get_unique_constraints("projects")
    unique_columns = [constraint["column_names"] for constraint in unique_constraints]

    return ["repository_path"] in unique_columns
