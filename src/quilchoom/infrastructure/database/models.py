"""
Defines SQLAlchemy models used to persist Quilchoom's
domain data.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    repository_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class EventModel(Base):
    __tablename__ = "events"

    __table_args__ = (
        Index("ix_events_project_id_timestamp", "project_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        nullable=False,
    )
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_reference: Mapped[str] = mapped_column(String, nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )
