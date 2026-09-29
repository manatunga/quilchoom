"""
Defines the Project domain object.
"""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Project(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    repository_path: Path
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
