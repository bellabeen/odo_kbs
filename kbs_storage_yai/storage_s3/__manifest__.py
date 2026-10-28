# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Storage S3 Driver",
    "summary": "Amazon S3 / S3-compatible backend for KBS Storage Core",
    "version": "1.0.0",
    "category": "Technical",
    "author": "Solution Architecture Team",
    "website": "https://apps.odoo.com",
    "license": "LGPL-3",
    "depends": ["storage_core"],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
    "external_dependencies": {"python": ["boto3", "botocore"]},
}
