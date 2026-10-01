"""
Defines application-level errors for Quilchoom.
"""


class ProjectInitializationError(Exception):
    """Raised when a Quilchoom project cannot be initialized."""


class HistoryReconstructionError(Exception):
    """Raised when a project's development history cannot be reconstructed."""
