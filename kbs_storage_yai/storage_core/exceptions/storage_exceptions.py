"""Typed exception tree for storage failures.

Every public driver call MUST raise one of these. Never propagate SDK
exceptions raw across the abstraction boundary (ADR-001).
"""

from __future__ import annotations

from typing import Optional


class StorageError(Exception):
    """Base class for all storage framework errors."""

    def __init__(
        self,
        message: str,
        *,
        backend: Optional[str] = None,
        key: Optional[str] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.backend: Optional[str] = backend
        self.key: Optional[str] = key
        self.cause: Optional[BaseException] = cause


class StorageConfigurationError(StorageError):
    """Invalid or incomplete backend configuration."""


class StorageConnectionError(StorageError):
    """Network or connectivity failure against the provider."""


class StorageAuthenticationError(StorageError):
    """Credential, IAM, or permission failure (ADR-007)."""


class ObjectNotFoundError(StorageError):
    """Requested object key does not exist on the backend."""


class BackendNotFoundError(StorageError):
    """Backend name not registered in the BackendRegistry."""


class UnsupportedOperationError(StorageError):
    """Driver does not implement the requested optional operation
    (e.g. generate_url on a backend without URL support)."""


class StorageOperationError(StorageError):
    """Generic operational failure not covered by a narrower type."""
