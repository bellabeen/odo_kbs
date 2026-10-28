"""Local filesystem provider.

Config keys (see BackendRegistry.get(config)):
    root: absolute base path (required)
    url_prefix: optional public URL root for generate_url
"""

from __future__ import annotations

import errno
import mimetypes
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterator, Optional, Union

from storage_core.domain import ObjectMetadata
from storage_core.exceptions import (
    ObjectNotFoundError,
    StorageConfigurationError,
    StorageOperationError,
)
from storage_core.interfaces import StorageBackend
from storage_core.utils import sha256_file, sha256_stream

Readable = Union[bytes, BinaryIO, Iterator[bytes]]


class LocalStorageDriver(StorageBackend):
    """Stores objects under `<root>/<bucket>/<object_key>`.

    Bucket becomes a directory. Atomic writes via temp file + os.replace.
    Streaming reads. No presigned URLs by default; override
    `generate_url` with `url_prefix` for nginx/CDN fronted mounts.
    """

    backend_code = "local"

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        root = cfg.get("root")
        if not root:
            raise StorageConfigurationError(
                "storage_local requires 'root' in config",
                backend=self.backend_code,
            )
        self.root: Path = Path(root).expanduser().resolve(strict=False)
        self.bucket: str = cfg.get("bucket", "default")
        self.url_prefix: Optional[str] = cfg.get("url_prefix")
        self.root.mkdir(parents=True, exist_ok=True)

    # ---------- helpers ----------

    def _abs_path(self, key: str) -> Path:
        """Resolve key under root/bucket. Refuse escape + traversal.

        Bucket pinned at construction — cross-bucket rename is a service
        concern, not driver's. Keys treated as opaque subpaths.
        """
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise StorageOperationError(
                f"invalid key {key!r}",
                backend=self.backend_code,
                key=key,
            )
        base = (self.root / self.bucket).resolve(strict=False)
        target = (base / key).resolve(strict=False)
        try:
            target.relative_to(base)
        except ValueError as err:
            raise StorageOperationError(
                f"key escapes bucket root: {key!r}",
                backend=self.backend_code,
                key=key,
                cause=err,
            )
        return target

    # ---------- interface ----------

    def write(
        self,
        key: str,
        payload: Readable,
        *,
        mime: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ObjectMetadata:
        target = self._abs_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic: write tmp in same dir, then rename.
        fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=str(target.parent))
        try:
            if isinstance(payload, (bytes, bytearray)):
                with os.fdopen(fd, "wb") as fh:
                    fh.write(payload)
            else:
                with os.fdopen(fd, "wb") as fh:
                    if hasattr(payload, "read"):
                        shutil.copyfileobj(payload, fh, length=1024 * 1024)  # type: ignore[arg-type]
                    else:
                        for chunk in payload:  # type: ignore[union-attr]
                            fh.write(chunk)
            os.replace(tmp, target)
        except Exception as err:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise StorageOperationError(
                f"write failed for {key!r}",
                backend=self.backend_code,
                key=key,
                cause=err,
            ) from err

        stat = target.stat()
        return ObjectMetadata(
            backend=self.backend_code,
            bucket=str(target.parent.relative_to(self.root)),
            object_key=key,
            checksum=sha256_file(target),
            size=stat.st_size,
            mime=mime
            or mimetypes.guess_type(key)[0]
            or "application/octet-stream",
            created=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).replace(tzinfo=None),
            modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(tzinfo=None),
        )

    def read(self, key: str) -> bytes:
        target = self._abs_path(key)
        try:
            with open(target, "rb") as fh:
                return fh.read()
        except FileNotFoundError as err:
            raise ObjectNotFoundError(
                f"object {key!r} not found",
                backend=self.backend_code,
                key=key,
                cause=err,
            ) from err

    def stream(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        target = self._abs_path(key)
        if not target.exists():
            raise ObjectNotFoundError(
                f"object {key!r} not found",
                backend=self.backend_code,
                key=key,
            )
        with open(target, "rb") as fh:
            while True:
                block = fh.read(chunk_size)
                if not block:
                    return
                yield block

    def delete(self, key: str) -> None:
        target = self._abs_path(key)
        try:
            target.unlink()
        except FileNotFoundError:
            return  # idempotent (ADR-005)
        except OSError as err:
            raise StorageOperationError(
                f"delete failed for {key!r}",
                backend=self.backend_code,
                key=key,
                cause=err,
            ) from err

    def exists(self, key: str) -> bool:
        return self._abs_path(key).exists()

    def head(self, key: str) -> ObjectMetadata:
        target = self._abs_path(key)
        if not target.exists():
            raise ObjectNotFoundError(
                f"object {key!r} not found",
                backend=self.backend_code,
                key=key,
            )
        stat = target.stat()
        return ObjectMetadata(
            backend=self.backend_code,
            bucket=str(target.parent.relative_to(self.root)),
            object_key=key,
            checksum=sha256_file(target),
            size=stat.st_size,
            mime=mimetypes.guess_type(key)[0] or "application/octet-stream",
            created=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).replace(tzinfo=None),
            modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(tzinfo=None),
        )

    def copy(self, source: str, target: str) -> ObjectMetadata:
        src = self._abs_path(source)
        dst = self._abs_path(target)
        if not src.exists():
            raise ObjectNotFoundError(
                f"source {source!r} not found",
                backend=self.backend_code,
                key=source,
            )
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return self.head(target)

    def move(self, source: str, target: str) -> ObjectMetadata:
        src = self._abs_path(source)
        dst = self._abs_path(target)
        if not src.exists():
            raise ObjectNotFoundError(
                f"source {source!r} not found",
                backend=self.backend_code,
                key=source,
            )
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return self.head(target)

    def list(self, prefix: str = "", limit: Optional[int] = None) -> Iterator[str]:
        base = self.root / self.bucket
        if not base.exists():
            return
        seen = 0
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(base))
            if prefix and not rel.startswith(prefix):
                continue
            yield rel
            seen += 1
            if limit is not None and seen >= limit:
                return

    def checksum(self, key: str) -> str:
        target = self._abs_path(key)
        if not target.exists():
            raise ObjectNotFoundError(
                f"object {key!r} not found",
                backend=self.backend_code,
                key=key,
            )
        return sha256_file(target)

    def generate_url(
        self,
        key: str,
        *,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        if not self.url_prefix:
            return super().generate_url(key, expires_in=expires_in, method=method)
        if method != "GET":
            raise StorageOperationError(
                "local backend supports GET URLs only",
                backend=self.backend_code,
                key=key,
            )
        # ponytail: no signature/expiry. Upgrade path = reverse-proxy with auth_request or token param.
        return f"{self.url_prefix.rstrip('/')}/{key}"

    def healthcheck(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            probe = self.root / ".storage_health_probe"
            with open(probe, "wb") as fh:
                fh.write(b"ok")
            probe.unlink(missing_ok=True)
            return True
        except OSError as err:
            if err.errno in (errno.EACCES, errno.EROFS):
                return False
            return False
