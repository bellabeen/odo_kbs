# Enterprise Storage Framework for Odoo

Cloud-native, pluggable storage abstraction for Odoo attachments.
Community + Enterprise · Odoo 17+ / 18+ · Python 3.11+ · PostgreSQL 14+.

## Modules

| Module | Purpose | Depends on |
|---|---|---|
| `storage_core` | Interfaces, registry, services, metadata model, exceptions | `base` |
| `storage_local` | Local filesystem driver | `storage_core` |
| `storage_s3` | AWS S3 driver | `storage_core`, `boto3` |
| `storage_minio` | MinIO driver | `storage_core`, `minio` |
| `storage_gcs` | Google Cloud Storage driver | `storage_core`, `google-cloud-storage` |
| `storage_azure` | Azure Blob driver | `storage_core`, `azure-storage-blob` |
| `storage_r2` | Cloudflare R2 driver | `storage_core`, `boto3` (S3-compat) |
| `storage_dashboard` | Analytics UI | `storage_core` |
| `storage_security` | Encryption / secrets | `storage_core` |
| `storage_monitoring` | Prometheus / OpenTelemetry | `storage_core` |
| `storage_migration` | Cross-backend migration wizard | `storage_core` |

**Technical model name (locked):** `kbs.storage.backend` — Odoo model for backend config records.
`kbs_` prefix avoids collision with other vendor modules.

## Installation

### Add to Odoo addons-path

```bash
# In odoo.conf
addons_path = /path/to/odoo/addons,/path/to/kbs_storage_yai

# Or via command line
odoo-bin --addons-path=/path/to/odoo/addons,/path/to/kbs_storage_yai
```

Install modules in Odoo:
```bash
odoo-bin --addons-path=... -d your_database -i storage_core,storage_local,storage_s3
```

## AWS S3 Setup

### Option 1: EC2/ECS (Recommended — ADR-007)

Attach IAM role to EC2 instance or ECS task. No credentials needed. Boto3 auto-discovers role.

**IAM Policy** (least privilege, replace `your-bucket-name`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::your-bucket-name"
    },
    {
      "Sid": "ObjectReadWrite",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:GetObject",
        "s3:HeadObject",
        "s3:DeleteObject",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### Option 2: On-Premise (Access Key)

Set env vars or Odoo config:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

Or in Odoo UI: Settings → Storage → Add Backend (S3) → Paste credentials.

## Local Storage Setup

Settings → Storage → Add Backend (Local) → Set root directory (e.g., `/var/odoo/attachments`).

## Testing

```bash
python run_tests.py
```

Runs compile check + unit + integration tests (8/8 green).

## Documentation

- [PRD](PRD.md)
- [Architecture Design](ArchitectureDesign.md)
- [ADR Index](ADR/)

## Status

Phase 7 complete — Ready for production deployment with `storage_core`, `storage_local`, and `storage_s3` modules. See [prompt.md](prompt.md) for phase plan.

## License

LGPL-3.0
