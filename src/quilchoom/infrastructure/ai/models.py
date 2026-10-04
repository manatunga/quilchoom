"""
Defines AI-facing data models for Quilchoom's structured AI operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from quilchoom.domain.knowledge_claim import ClaimBasis, ClaimConfidence


class AIProjectInput(BaseModel):
    """Represents project information deliberately exposed to an AI operation."""

    model_config = ConfigDict(extra="forbid")

    name: str


class AIEventInput(BaseModel):
    """Represents development event information deliberately exposed to an AI operation."""

    model_config = ConfigDict(extra="forbid")

    type: str
    timestamp: datetime
    summary: str
    source: str
    source_reference: str


class AIEvidenceInput(BaseModel):
    """Represents evidence information deliberately exposed to an AI operation."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    type: str
    content: str | None
    reference: str | None
    source: str


class AIHistoryEntryInput(BaseModel):
    """Represents a development history entry exposed to an AI operation."""

    model_config = ConfigDict(extra="forbid")

    event: AIEventInput
    evidence: AIEvidenceInput


class AIActiveClaimInput(BaseModel):
    """Represents an active knowledge claim exposed to an AI operation."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    statement: str
    basis: ClaimBasis
    confidence: ClaimConfidence


class AIInterpretationInput(BaseModel):
    """Represents the complete structured input for AI knowledge interpretation."""

    model_config = ConfigDict(extra="forbid")

    project: AIProjectInput
    entries: list[AIHistoryEntryInput] = Field(min_length=1)
    active_claims: list[AIActiveClaimInput] = Field(default_factory=list)


class AIClaimCandidate(BaseModel):
    """Represents a knowledge claim candidate proposed by an AI operation."""

    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1)
    basis: ClaimBasis
    confidence: ClaimConfidence
    evidence_ids: list[UUID] = Field(min_length=1)


class AIInterpretationOutput(BaseModel):
    """Represents structured AI output for knowledge interpretation."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[AIClaimCandidate] = Field(default_factory=list)
