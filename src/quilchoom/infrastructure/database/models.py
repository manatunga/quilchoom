"""
Defines SQLAlchemy models used to persist Quilchoom's
domain data.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from quilchoom.domain.document import DocumentVersionOrigin
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
)


class Base(DeclarativeBase):
    pass


knowledge_claim_evidence = Table(
    "knowledge_claim_evidence",
    Base.metadata,
    Column(
        "claim_id",
        ForeignKey("knowledge_claims.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


document_version_claims = Table(
    "document_version_claims",
    Base.metadata,
    Column(
        "document_version_id",
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "claim_id",
        ForeignKey("knowledge_claims.id", ondelete="CASCADE"),
        primary_key=True,
        unique=True,
    ),
)


interpretation_run_evidence = Table(
    "interpretation_run_evidence",
    Base.metadata,
    Column(
        "interpretation_run_id",
        ForeignKey("interpretation_runs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
        unique=True,
    ),
)


interpretation_run_claims = Table(
    "interpretation_run_claims",
    Base.metadata,
    Column(
        "interpretation_run_id",
        ForeignKey("interpretation_runs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "claim_id",
        ForeignKey("knowledge_claims.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


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
        UniqueConstraint(
            "project_id",
            "source",
            "source_reference",
            name="uq_events_project_source_reference",
        ),
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


class EvidenceModel(Base):
    __tablename__ = "evidence"

    __table_args__ = (
        Index("ix_evidence_project_id_captured_at", "project_id", "captured_at"),
        UniqueConstraint(
            "project_id",
            "source",
            "reference",
            name="uq_evidence_project_source_reference",
        ),
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
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(String, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source: Mapped[str] = mapped_column(String, nullable=False)
    evidence_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    claims: Mapped[list[KnowledgeClaimModel]] = relationship(
        secondary=knowledge_claim_evidence,
        back_populates="evidence",
    )
    interpretation_runs: Mapped[list[InterpretationRunModel]] = relationship(
        secondary=interpretation_run_evidence,
        back_populates="evidence",
    )


def ValuedEnum(
    enum_cls: type[ClaimBasis | ClaimConfidence | ClaimStatus | DocumentVersionOrigin],
) -> SQLAlchemyEnum:
    return SQLAlchemyEnum(enum_cls, values_callable=lambda cls: [m.value for m in cls])


class KnowledgeClaimModel(Base):
    __tablename__ = "knowledge_claims"

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
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    basis: Mapped[ClaimBasis] = mapped_column(
        ValuedEnum(ClaimBasis),
        nullable=False,
    )
    confidence: Mapped[ClaimConfidence] = mapped_column(
        ValuedEnum(ClaimConfidence),
        nullable=False,
    )
    status: Mapped[ClaimStatus] = mapped_column(
        ValuedEnum(ClaimStatus),
        nullable=False,
    )

    evidence: Mapped[list[EvidenceModel]] = relationship(
        secondary=knowledge_claim_evidence,
        back_populates="claims",
    )
    document_versions: Mapped[list[DocumentVersionModel]] = relationship(
        secondary=document_version_claims,
        back_populates="claims",
    )
    interpretation_runs: Mapped[list[InterpretationRunModel]] = relationship(
        secondary=interpretation_run_claims,
        back_populates="claims",
    )


class CorrectionModel(Base):
    __tablename__ = "corrections"

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
    target_claim_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("knowledge_claims.id"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    replacement_claim_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("knowledge_claims.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DocumentModel(Base):
    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "key",
            name="uq_documents_project_key",
        ),
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
    key: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DocumentVersionModel(Base):
    __tablename__ = "document_versions"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_version_number",
        ),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[DocumentVersionOrigin] = mapped_column(
        ValuedEnum(DocumentVersionOrigin),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    claims: Mapped[list[KnowledgeClaimModel]] = relationship(
        secondary=document_version_claims,
        back_populates="document_versions",
    )


class InterpretationRunModel(Base):
    __tablename__ = "interpretation_runs"

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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    evidence: Mapped[list[EvidenceModel]] = relationship(
        secondary=interpretation_run_evidence,
        back_populates="interpretation_runs",
    )
    claims: Mapped[list[KnowledgeClaimModel]] = relationship(
        secondary=interpretation_run_claims,
        back_populates="interpretation_runs",
    )
