"""
Defines provider-neutral errors for Quilchoom's AI infrastructure.
"""


class AIError(Exception):
    """Base exception for failures in Quilchoom's AI infrastructure."""


class AIConfigurationError(AIError):
    """Raised when AI infrastructure is not configured for execution."""


class AIAuthenticationError(AIError):
    """Raised when an AI provider rejects configured credentials."""


class AIConnectionError(AIError):
    """Raised when an AI provider cannot be reached reliably."""


class AIRateLimitError(AIError):
    """Raised when an AI provider temporarily limits requests."""


class AIContextLimitError(AIError):
    """Raised when an AI request exceeds the model's supported context."""


class AIResponseError(AIError):
    """Raised when AI generation does not produce a usable requested response."""


class AIProviderError(AIError):
    """Raised when an AI provider fails without a more specific error category."""
