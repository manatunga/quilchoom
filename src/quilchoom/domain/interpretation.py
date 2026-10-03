"""
Defines the domain objects used for knowledge interpretation.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from quilchoom.domain.history import HistoryEntry
from quilchoom.domain.knowledge_claim import ClaimBasis, ClaimConfidence, KnowledgeClaim
from quilchoom.domain.project import Project


class InterpretationContext(BaseModel):
    project: Project
    entries: list[HistoryEntry] = Field(min_length=1)
    active_claims: list[KnowledgeClaim] = Field(default_factory=list)


class ClaimCandidate(BaseModel):
    statement: str = Field(min_length=1)
    basis: ClaimBasis
    confidence: ClaimConfidence
    evidence_ids: list[UUID] = Field(min_length=1)


class InterpretationResult(BaseModel):
    candidates: list[ClaimCandidate] = Field(default_factory=list)


class InterpretationRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    evidence_ids: list[UUID] = Field(min_length=1)
    claim_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
