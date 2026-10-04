"""
Defines non-secret configuration for Quilchoom's AI infrastructure.
"""

from pydantic import BaseModel


class AIConfig(BaseModel):
    """Defines non-secret configuration for an AI provider."""

    provider: str
    model: str
    endpoint: str | None = None
