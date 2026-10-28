"""ir.attachment inheritance (ADR-008 — no core modification).

Hooks:
  _file_write  — route bytes through AttachmentService when an external
                 backend is the default; otherwise defer to super (filestore).
  _file_read   — recognise `kbs://<object_id>` pseudo-fname and stream back.

Backward compat: zero rows in `kbs.storage.backend` → 100% stock Odoo
behaviour. Presence of a default backend flips routing.
"""

from __future__ import annotations

import logging
from typing import Optional

from odoo import fields, models

_logger = logging.getLogger(__name__)

_SCHEME = "kbs://"


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    storage_object_id = fields.Many2one(
        "kbs.storage.object",
        index=True,
        ondelete="restrict",
        help="External stored-object row (ADR-003). Populated by AttachmentService.",
    )

    # ---------- helpers ----------

    def _kbs_default_backend(self):
        """Default active external backend, or empty recordset."""
        return (
            self.env["kbs.storage.backend"]
            .sudo()
            .search([("is_default", "=", True), ("active", "=", True)], limit=1)
        )

    @staticmethod
    def _kbs_parse_fname(store_fname: str) -> Optional[int]:
        """Return object id if fname uses kbs:// scheme."""
        if store_fname and store_fname.startswith(_SCHEME):
            try:
                return int(store_fname[len(_SCHEME):])
            except ValueError:
                return None
        return None

    # ---------- hooks ----------

    def _file_write(self, value, checksum):  # noqa: D401 — keep stock signature
        """Write path. Falls back to super() when no default backend set."""
        backend = self._kbs_default_backend()
        if not backend:
            return super()._file_write(value, checksum)

        service = self.env["kbs.storage.service"].sudo()
        object_id, pseudo_fname = service.put(
            value,
            name=self.name or "attachment",
            mimetype=self.mimetype or None,
            backend_id=backend.id,
            company_id=self.company_id.id or None,
        )
        # Mirror stock behaviour — Odoo core returns store_fname; we return
        # pseudo scheme so _file_read knows how to resolve.
        self.storage_object_id = object_id
        _logger.info(
            "attachment routed to external backend",
            extra={
                "attachment_id": self.id or "<new>",
                "object_id": object_id,
                "backend": backend.backend_code,
            },
        )
        return pseudo_fname

    def _file_read(self, fname):  # noqa: D401
        """Read path. kbs://<id> → service.get_bytes; else super()."""
        object_id = self._kbs_parse_fname(fname or "")
        if object_id is None:
            return super()._file_read(fname)
        return self.env["kbs.storage.service"].sudo().get_bytes(object_id)

    def unlink(self):
        """Release external refs (ref_count--) when attachment deleted."""
        service = self.env["kbs.storage.service"].sudo()
        for att in self:
            if att.storage_object_id:
                service.drop(att.storage_object_id.id)
        return super().unlink()
