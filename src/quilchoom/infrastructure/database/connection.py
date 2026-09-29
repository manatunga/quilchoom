"""
Creates database engines and initializes Quilchoom's database schema.
"""

from pathlib import Path

from sqlalchemy import Engine, create_engine

from quilchoom.infrastructure.database.models import Base


def create_database_engine(database_path: Path):
    return create_engine(f"sqlite:///{database_path}")


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
