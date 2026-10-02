"""
Defines the Document and DocumentVersion domain objects and supporting enums.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentVersionOrigin(Enum):
    GENERATED = "generated"
    MANUAL = "manual"
    IMPORTED = "imported"


class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    key: str
    kind: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DocumentVersion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    version_number: int = Field(ge=1)
    content: str = Field(min_length=1)
    origin: DocumentVersionOrigin
    claim_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
