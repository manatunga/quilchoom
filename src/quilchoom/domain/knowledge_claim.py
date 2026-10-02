"""
Defines the KnowledgeClaim domain object and its supporting enums.
"""

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ClaimConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimStatus(str, Enum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    INVALIDATED = "invalidated"


class KnowledgeClaim(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    statement: str
    confidence: ClaimConfidence
    status: ClaimStatus
    evidence_ids: list[UUID] = Field(min_length=1)
