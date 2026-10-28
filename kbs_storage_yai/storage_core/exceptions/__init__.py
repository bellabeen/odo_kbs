"""Exception hierarchy for the storage framework."""

from .storage_exceptions import (
    BackendNotFoundError,
    ObjectNotFoundError,
    StorageAuthenticationError,
    StorageConfigurationError,
    StorageConnectionError,
    StorageError,
    StorageOperationError,
    UnsupportedOperationError,
)

__all__ = [
    "StorageError",
    "BackendNotFoundError",
    "ObjectNotFoundError",
    "StorageAuthenticationError",
    "StorageConfigurationError",
    "StorageConnectionError",
    "StorageOperationError",
    "UnsupportedOperationError",
]
