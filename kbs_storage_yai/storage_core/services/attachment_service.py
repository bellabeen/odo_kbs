"""AttachmentService — orchestrator between ir.attachment and drivers.

ADR-001: business logic never imports provider SDKs here — only registry.
ADR-003: object metadata lives in `kbs.storage.object`, not on attachment.
ADR-005: providers are write-once; 'put' of existing key requires dedup hit.
ADR-006: SHA-256 content addressing enables dedup across attachments.
ADR-008: pure `_inherit`-based extension; no core modification.

Transactional caveat: driver.write happens inside the caller's DB tx. If tx
rolls back after a successful remote write, an orphan object is left behind.
Cleanup cron lands in Phase 8 — documented risk.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, BinaryIO, Optional, Tuple, Union

from odoo import api, models

from ..exceptions import (
    BackendNotFoundError,
    ObjectNotFoundError,
    StorageConfigurationError,
    StorageConnectionError,
    StorageOperationError,
)
from ..registry import get_default_registry
from ..utils import sha256_bytes
from ..utils.retry import retry

_logger = logging.getLogger(__name__)

Readable = Union[bytes, BinaryIO]
# Retry only transient classes; deterministic errors (config, auth) surface fast.
_RETRYABLE = (StorageConnectionError,)


class KbsStorageService(models.AbstractModel):
    """Orchestrates put/get/delete through the registry.

    `_auto = True` but AbstractModel — no table, just a namespace with `env`.
    """

    _name = "kbs.storage.service"
    _description = "Storage Orchestrator Service"

    # ---------- backend resolution ----------

    @api.model
    def _resolve_backend_record(
        self, backend_id: Optional[int] = None, company_id: Optional[int] = None,
    ):
        """Pick `kbs.storage.backend` row: explicit > default flag > settings param."""
        Backend = self.env["kbs.storage.backend"].sudo()
        if backend_id:
            rec = Backend.browse(backend_id)
            if not rec.exists():
                raise StorageConfigurationError(f"backend id {backend_id} not found")
            return rec
        if company_id:
            rec = Backend.search(
                [("company_id", "=", company_id), ("is_default", "=", True)],
                limit=1,
            )
            if rec:
                return rec
        rec = Backend.search([("is_default", "=", True)], limit=1)
        if rec:
            return rec
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("kbs_storage.default_backend_id")
        )
        if param:
            rec = Backend.browse(int(param))
            if rec.exists():
                return rec
        return Backend.browse()  # empty recordset → caller falls back to default Odoo

    @api.model
    def _build_driver(self, backend_rec):
        """Build StorageBackend from kbs.storage.backend row."""
        if not backend_rec:
            raise StorageConfigurationError("no backend record")
        try:
            options = json.loads(backend_rec.options_json or "{}")
        except (TypeError, ValueError) as err:
            raise StorageConfigurationError(
                "invalid options_json", backend=backend_rec.backend_code, cause=err,
            ) from err
        cfg: dict[str, Any] = {
            "bucket": backend_rec.bucket or None,
            "region": backend_rec.region or None,
            "endpoint_url": backend_rec.endpoint or None,
            **{k: v for k, v in options.items() if v not in (None, "")},
        }
        return get_default_registry().get(backend_rec.backend_code, cfg)

    # ---------- public API ----------

    @api.model
    def put(
        self,
        payload: Readable,
        *,
        name: str,
        mimetype: Optional[str] = None,
        backend_id: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> Tuple[int, str]:
        """Store payload; return (kbs.storage.object id, pseudo store_fname).

        Pseudo fname has form `kbs://<object_id>`; ir.attachment stores it
        in `store_fname` and resolves via `_file_read`.
        """
        backend_rec = self._resolve_backend_record(backend_id, company_id)
        if not backend_rec:
            raise BackendNotFoundError("no external storage backend configured")
        driver = self._build_driver(backend_rec)

        raw: bytes
        if isinstance(payload, (bytes, bytearray)):
            raw = bytes(payload)
        elif hasattr(payload, "read"):
            raw = payload.read()
        else:
            raise TypeError(f"unsupported payload {type(payload)!r}")
        checksum = sha256_bytes(raw)
        size = len(raw)

        # ADR-006 dedup: same checksum + size on this backend → reuse.
        Obj = self.env["kbs.storage.object"].sudo()
        existing = Obj.search(
            [
                ("backend_id", "=", backend_rec.id),
                ("checksum", "=", checksum),
                ("size", "=", size),
            ],
            limit=1,
        )
        if existing:
            existing.write({"ref_count": existing.ref_count + 1})
            _logger.info(
                "dedup hit",
                extra={"object_id": existing.id, "checksum": checksum},
            )
            return existing.id, f"kbs://{existing.id}"

        object_key = f"{checksum[:2]}/{checksum}"
        metadata = {"sha256": checksum, "name": name}

        @retry(attempts=3, backoff=0.5, retryable=_RETRYABLE)
        def _write() -> Any:
            return driver.write(
                object_key, raw, mime=mimetype, metadata=metadata,
            )

        meta = _write()
        obj = Obj.create(
            {
                "name": name,
                "backend_id": backend_rec.id,
                "object_key": object_key,
                "bucket": backend_rec.bucket or "",
                "checksum": checksum,
                "size": size,
                "mime": mimetype or meta.mime,
                "etag": meta.etag or "",
                "version_id": meta.version_id or "",
                "ref_count": 1,
                "state": "stored",
            }
        )
        return obj.id, f"kbs://{obj.id}"

    @api.model
    def get_bytes(self, object_id: int) -> bytes:
        """Bound-checked read. Prefer `stream` for large objects."""
        obj = self.env["kbs.storage.object"].sudo().browse(object_id)
        if not obj.exists():
            raise ObjectNotFoundError(f"object {object_id}", backend=None)
        driver = self._build_driver(obj.backend_id)

        @retry(attempts=3, backoff=0.5, retryable=_RETRYABLE)
        def _read() -> bytes:
            return driver.read(obj.object_key)

        return _read()

    @api.model
    def get_stream(self, object_id: int, chunk_size: int = 64 * 1024):
        """Iterator yielding chunks. Caller closes implicitly by exhausting."""
        obj = self.env["kbs.storage.object"].sudo().browse(object_id)
        if not obj.exists():
            raise ObjectNotFoundError(f"object {object_id}", backend=None)
        driver = self._build_driver(obj.backend_id)
        yield from driver.stream(obj.object_key, chunk_size=chunk_size)

    @api.model
    def drop(self, object_id: int) -> None:
        """Decrement ref_count; remote delete at zero. ADR-005 keeps this rare."""
        obj = self.env["kbs.storage.object"].sudo().browse(object_id)
        if not obj.exists():
            return
        if obj.ref_count > 1:
            obj.write({"ref_count": obj.ref_count - 1})
            return
        driver = self._build_driver(obj.backend_id)
        try:
            driver.delete(obj.object_key)
        except ObjectNotFoundError:
            pass
        obj.unlink()

    # ---------- base64 convenience ----------

    @api.model
    def put_b64(self, b64: str, **kw) -> Tuple[int, str]:
        return self.put(base64.b64decode(b64), **kw)

    @api.model
    def get_b64(self, object_id: int) -> str:
        return base64.b64encode(self.get_bytes(object_id)).decode("ascii")
