"""StorageBackend abstract interface (ADR-001).

Provider modules implement `StorageBackend`. Business logic only sees
this interface — never provider SDKs.
"""

from .storage_backend import StorageBackend

__all__ = ["StorageBackend"]
