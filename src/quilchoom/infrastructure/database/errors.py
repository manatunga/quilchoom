"""
Defines errors raised by Quilchoom's database infrastructure.
"""


class DatabaseMigrationError(Exception):
    """Raised when a Quilchoom database cannot be migrated safely."""


class EvidenceNotFoundError(Exception):
    """Raised when referenced evidence cannot be found in the database."""


class EvidenceProjectMismatchError(Exception):
    """Raised when claim evidence belongs to a different project."""


class KnowledgeClaimNotFoundError(Exception):
    """Raised when a knowledge claim cannot be found in the database."""


class DocumentNotFoundError(Exception):
    """Raised when a referenced document cannot be found."""


class KnowledgeClaimProjectMismatchError(Exception):
    """Raised when a knowledge claim belongs to a different project."""
