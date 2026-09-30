"""
Defines the Evidence domain object.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    type: str
    content: str | None = None
    reference: str | None = None
    captured_at: datetime
    source: str
    metadata: dict[str, object] | None = None
