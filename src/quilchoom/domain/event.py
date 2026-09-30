"""
Defines the Event domain object.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    type: str
    timestamp: datetime
    summary: str
    source: str
    source_reference: str
    metadata: dict[str, object] | None = None
