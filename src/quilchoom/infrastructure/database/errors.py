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


class DocumentVersionMismatchError(Exception):
    """Raised when a document version does not belong to its target document."""


class InvalidInitialDocumentVersionError(Exception):
    """Raised when an initial document version does not have version number one."""


class KnowledgeClaimProjectMismatchError(Exception):
    """Raised when a knowledge claim belongs to a different project."""


class InvalidInterpretationRunError(Exception):
    """Raised when an interpretation run is inconsistent with its claims."""


class ProjectNotFoundError(Exception):
    """Raised when a referenced project cannot be found in the database."""


class EventEvidenceMismatchError(Exception):
    """Raised when an event and its supporting evidence do not describe the same activity."""
