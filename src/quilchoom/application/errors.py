"""
Defines application-level errors for Quilchoom.
"""


class ProjectInitializationError(Exception):
    """Raised when a Quilchoom project cannot be initialized."""


class HistoryReconstructionError(Exception):
    """Raised when a project's development history cannot be reconstructed."""


class CorrectionProjectMismatchError(Exception):
    """Raised when a correction references a claim from another project."""


class SelfReplacementError(Exception):
    """Raised when a claim is used as its own replacement."""
