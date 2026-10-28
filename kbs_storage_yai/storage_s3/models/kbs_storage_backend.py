"""Register 's3' backend code (ADR-002, ADR-007)."""

from __future__ import annotations

from odoo import fields, models

from storage_core.registry import get_default_registry

from ..s3_driver import S3StorageDriver

get_default_registry().register("s3", lambda cfg: S3StorageDriver(cfg))


class KbsStorageBackend(models.Model):
    _inherit = "kbs.storage.backend"

    backend_code = fields.Selection(
        selection_add=[("s3", "Amazon S3 / S3-Compatible")],
        ondelete={"s3": "set null"},
    )
