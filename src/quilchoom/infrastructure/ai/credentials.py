"""
Resolves credentials for Quilchoom's AI infrastructure.
"""

import os

from quilchoom.infrastructure.ai.errors import AIConfigurationError


def resolve_environment_credential(variable_name: str) -> str:
    """Resolve a required AI credential from an environment variable."""

    credential = os.environ.get(variable_name)

    if not credential or not credential.strip():
        raise AIConfigurationError(
            f"Environment variable '{variable_name}' is missing or empty."
        )

    return credential.strip()
