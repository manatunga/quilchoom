"""
Defines the Correction domain object.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Correction(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    target_claim_id: UUID
    reason: str
    replacement_claim_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
