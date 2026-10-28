"""HTTP streaming endpoint for stored objects (ADR-004).

Route: GET /kbs/storage/object/<id>/download

Reads attachment's ACL via `ir.attachment` record rules then streams bytes
from the backend without materializing the whole payload in RAM.
"""

from __future__ import annotations

import logging
from typing import Iterator

from odoo import http
from odoo.exceptions import AccessError, NotFound
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


class KbsStorageController(http.Controller):
    """Download controller. auth='user' — no public anonymous access."""

    @http.route(
        "/kbs/storage/object/<int:object_id>/download",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def download_object(self, object_id: int, **_kw) -> Response:
        """Stream object chunks back to the caller."""
        Obj = request.env["kbs.storage.object"].sudo()
        obj = Obj.browse(object_id)
        if not obj.exists():
            raise NotFound(f"storage object {object_id} not found")

        # ACL: must be able to read at least one ir.attachment pointing here.
        Att = request.env["ir.attachment"]
        attachment = Att.search([("storage_object_id", "=", obj.id)], limit=1)
        if not attachment:
            raise AccessError("no readable attachment for this object")

        service = Att.env["kbs.storage.service"].sudo()

        def _iterate() -> Iterator[bytes]:
            try:
                yield from service.get_stream(obj.id, chunk_size=64 * 1024)
            except Exception:
                _logger.exception(
                    "stream aborted", extra={"object_id": obj.id, "key": obj.object_key},
                )
                raise

        filename = attachment.name or obj.object_key
        headers = [
            ("Content-Type", attachment.mimetype or "application/octet-stream"),
            ("Content-Disposition", f'attachment; filename="{filename}"'),
            ("Cache-Control", "private, max-age=3600"),
        ]
        if obj.size:
            headers.append(("Content-Length", str(obj.size)))

        _logger.info(
            "stream start",
            extra={"object_id": obj.id, "bytes": obj.size, "user": request.uid},
        )
        return Response(_iterate(), status=200, headers=headers, direct_passthrough=True)
