"""
Defines errors raised by Quilchoom's database infrastructure.
"""


class DatabaseMigrationError(Exception):
    """Raised when a Quilchoom database cannot be migrated safely."""


class EvidenceNotFoundError(Exception):
    """Raised when referenced evidence cannot be found in the database."""


class EvidenceProjectMismatchError(Exception):
    """Raised when claim evidence belongs to a different project."""
