"""Immutable metadata describing one stored object.

Persists to `kbs.storage.object` (Odoo). Bytes live on the backend
(ADR-003). Never mutated in place — updates create new rows + GC old
(ADR-005).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    """One row of storage metadata.

    Attributes mirror ArchitectureDesign §10 and PRD §7 Metadata.
    """

    backend: str
    """Logical backend code, e.g. 's3', 'minio', 'local'."""

    bucket: str
    """Bucket / container / root path depending on driver."""

    object_key: str
    """Provider-side key. Treated as opaque by callers."""

    checksum: str
    """SHA-256 hex digest (ADR-006)."""

    size: int
    """Byte length. Always non-negative."""

    mime: str = "application/octet-stream"
    """IANA media type."""

    etag: Optional[str] = None
    """Provider-returned ETag if available."""

    storage_class: Optional[str] = None
    """Provider-side class: STANDARD, GLACIER, HOT, etc."""

    version_id: Optional[str] = None
    """Provider-side version identifier when versioning enabled."""

    region: Optional[str] = None
    """Backend region when provider supports it."""

    encryption: Optional[str] = None
    """At-rest scheme: 'SSE-S3' | 'SSE-KMS' | 'SSE-C' | 'AES256' | None."""

    kms_key_id: Optional[str] = None
    """KMS / CMK identifier when encryption uses it."""

    created: datetime = field(default_factory=datetime.utcnow)
    """UTC creation timestamp."""

    modified: Optional[datetime] = None
    """UTC last-modified timestamp (provider-reported)."""

    ref_count: int = 0
    """Active reference count for dedup GC (ADR-006)."""
