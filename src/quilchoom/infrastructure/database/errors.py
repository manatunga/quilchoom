"""
Defines errors raised by Quilchoom's database infrastructure.
"""


class DatabaseMigrationError(Exception):
    """Raised when a Quilchoom database cannot be migrated safely."""
