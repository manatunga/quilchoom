"""
Defines the interface and data contracts for document generation.
"""

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, Field

from quilchoom.domain.document import Document
from quilchoom.domain.knowledge_claim import KnowledgeClaim
from quilchoom.domain.project import Project


class DocumentGenerationContext(BaseModel):
    """Represents the project knowledge available for document generation."""

    project: Project
    document: Document
    claims: list[KnowledgeClaim] = Field(min_length=1)


class DocumentGenerationResult(BaseModel):
    """Represents generated document content and its claim provenance."""

    content: str = Field(min_length=1)
    claim_ids: list[UUID] = Field(min_length=1)


class DocumentGenerator(Protocol):
    """Defines the contract for generating documents from project knowledge."""

    def generate(
        self,
        context: DocumentGenerationContext,
    ) -> DocumentGenerationResult: ...
