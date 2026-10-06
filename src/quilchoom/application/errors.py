"""
Defines application-level errors for Quilchoom.
"""


class ProjectInitializationError(Exception):
    """Raised when a Quilchoom project cannot be initialized."""


class ProjectRuntimeError(Exception):
    """Raised when an existing Quilchoom project cannot be loaded."""


class HistoryReconstructionError(Exception):
    """Raised when a project's development history cannot be reconstructed."""


class CorrectionProjectMismatchError(Exception):
    """Raised when a correction references a claim from another project."""


class SelfReplacementError(Exception):
    """Raised when a claim is used as its own replacement."""


class InterpretationProjectMismatchError(Exception):
    """Raised when interpretation inputs belong to different projects."""


class InvalidCandidateEvidenceError(Exception):
    """Raised when an interpretation candidate references unavailable evidence."""


class NoActiveClaimsError(Exception):
    """Raised when document generation has no active knowledge claims."""


class InvalidGeneratedClaimError(Exception):
    """Raised when generated document provenance references an unavailable claim."""


class DocumentUnavailableError(Exception):
    """Raised when a requested project document has not been generated."""


class DocumentVersionUnavailableError(Exception):
    """Raised when a requested document version does not exist."""
