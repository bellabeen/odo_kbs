# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Storage Core",
    "summary": "Storage Abstraction Layer (SAL) for Odoo attachments",
    "version": "1.0.0",
    "category": "Technical",
    "author": "Solution Architecture Team",
    "website": "https://apps.odoo.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/kbs_storage_backend_views.xml",
        "views/kbs_storage_object_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False,
    "external_dependencies": {"python": []},
}
