"""Abstract StorageBackend interface (ADR-001, ADD §7).

Every provider module (storage_local, storage_s3, storage_minio, ...)
subclasses this. Business logic consumes only this type. Methods raise
`storage_core.exceptions.*` — never raw SDK exceptions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO, Iterator, Optional, Union

from ..domain import ObjectMetadata
from ..exceptions import UnsupportedOperationError

Readable = Union[bytes, BinaryIO, Iterator[bytes]]
"""Acceptable write payload. Bytes for small objects, stream for large."""


class StorageBackend(ABC):
    """Provider contract. Stateless, thread-safe, streaming-first (ADR-004).

    Implementation rules:
      - Objects are immutable post-write (ADR-005).
      - All downloads chunked via `stream`; no full-RAM reads.
      - All errors normalized to `storage_core.exceptions` types.
    """

    backend_code: str = ""
    """Unique registry key, e.g. 'local', 's3', 'minio'. Set by subclass."""

    # ---------- Write ----------

    @abstractmethod
    def write(
        self,
        key: str,
        payload: Readable,
        *,
        mime: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ObjectMetadata:
        """Persist `payload` under `key`. Returns resulting metadata.

        For large payloads MUST switch to multipart when provider
        supports it. Caller passes computed checksum independently —
        dedupe is a service concern (ADR-006), not driver concern.
        """

    # ---------- Read ----------

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Return full object bytes.

        Convenience over `stream()` for callers that know the size.
        Driver MAY enforce a max-size and fall back to stream raises
        `UnsupportedOperationError`.
        """

    @abstractmethod
    def stream(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """Yield object body in chunks (ADR-004).

        MUST not buffer the full object in memory and MUST not write
        a temporary local file (ADD §15).
        """

    # ---------- Delete / Inspect ----------

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove object. Idempotent: MISSING keys return silently."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True when key present."""

    @abstractmethod
    def head(self, key: str) -> ObjectMetadata:
        """Return metadata without fetching body."""

    # ---------- Movement ----------

    @abstractmethod
    def copy(self, source: str, target: str) -> ObjectMetadata:
        """Server-side copy when provider supports it."""

    @abstractmethod
    def move(self, source: str, target: str) -> ObjectMetadata:
        """Copy + delete atomically where possible."""

    @abstractmethod
    def list(self, prefix: str = "", limit: Optional[int] = None) -> Iterator[str]:
        """Yield keys under prefix. Order provider-specific."""

    # ---------- Checksum / URL / Health ----------

    @abstractmethod
    def checksum(self, key: str) -> str:
        """Return provider-native checksum, or computed SHA-256."""

    def generate_url(
        self,
        key: str,
        *,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        """Optional: presigned URL. Default raises Unsupported."""
        raise UnsupportedOperationError(
            f"{self.backend_code or type(self).__name__} does not support URLs",
            backend=self.backend_code,
            key=key,
        )

    @abstractmethod
    def healthcheck(self) -> bool:
        """Return True when backend reachable with current credentials."""
