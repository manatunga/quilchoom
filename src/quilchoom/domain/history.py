"""
Defines the domain objects used to represent reconstructed development history.
"""

from uuid import UUID

from pydantic import BaseModel

from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence


class HistoryEntry(BaseModel):
    event: Event
    evidence: Evidence


class DevelopmentHistory(BaseModel):
    project_id: UUID
    entries: list[HistoryEntry]
