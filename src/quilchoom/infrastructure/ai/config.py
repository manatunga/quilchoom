"""
Defines non-secret configuration for Quilchoom's AI infrastructure.
"""

from pydantic import BaseModel, ConfigDict


class AIConfig(BaseModel):
    """Defines non-secret configuration for an AI provider."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    endpoint: str | None = None
