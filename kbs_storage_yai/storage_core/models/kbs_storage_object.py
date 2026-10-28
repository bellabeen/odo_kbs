"""kbs.storage.object — one row per stored object (ADR-003, ADD §10).

Mirrors domain.ObjectMetadata. Bytes live on the backend; this row is
the authoritative handle. Updates create new rows (ADR-005).
"""

from __future__ import annotations

from odoo import fields, models


class KbsStorageObject(models.Model):
    _name = "kbs.storage.object"
    _description = "Stored Object Metadata"
    _rec_name = "object_key"
    _order = "id desc"

    backend_id = fields.Many2one(
        "kbs.storage.backend",
        required=True,
        ondelete="restrict",
        index=True,
    )
    bucket = fields.Char(required=True, index=True)
    object_key = fields.Char(required=True, index=True)
    checksum = fields.Char(required=True, index=True, help="SHA-256 hex (ADR-006).")
    size = fields.Integer(required=True)
    mime = fields.Char(default="application/octet-stream")
    etag = fields.Char()
    storage_class = fields.Char()
    version_id = fields.Char()
    region = fields.Char()
    encryption = fields.Char(help="SSE-S3 | SSE-KMS | SSE-C | AES256")
    kms_key_id = fields.Char()
    ref_count = fields.Integer(default=0, index=True, help="ADR-006 GC input.")

    _sql_constraints = [
        (
            "uniq_backend_key",
            "unique(backend_id, bucket, object_key, version_id)",
            "Duplicate object on backend.",
        ),
    ]
