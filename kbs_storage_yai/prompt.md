You are a Principal Odoo Software Engineer, Python Architect, Cloud Solution Architect, AWS Storage Specialist, DevSecOps Engineer, and OCA Contributor.

Your task is to build an Enterprise-grade Object Storage Framework for Odoo.

This module must be production-ready, cloud-native, highly scalable, secure, extensible, fully documented, and compatible with Odoo Community and Enterprise.

Target compatibility:

- Odoo 17.0
- Odoo 18.0
- Future-ready for Odoo 19+
- Python 3.11+
- PostgreSQL 14+
- Docker
- Kubernetes
- ECS
- On-premise
- Multi-company
- Multi-database

====================================================
GOALS
====================================================

Create a generic Storage Abstraction Layer (SAL).

Odoo should never know whether a file is stored in:

- Local filesystem
- NFS
- EFS
- S3
- MinIO
- Google Cloud Storage
- Azure Blob Storage
- Cloudflare R2
- Backblaze B2
- Wasabi
- DigitalOcean Spaces
- Any future Object Storage

The storage backend must be pluggable.

====================================================
ARCHITECTURE
====================================================

Use clean architecture.

Presentation Layer

↓

Service Layer

↓

Storage Abstraction Layer

↓

Backend Driver

↓

Storage Provider

No business logic should directly call boto3 or cloud SDK.

Everything must go through an abstract interface.

Example

StorageBackend

write()

read()

delete()

exists()

list()

copy()

move()

generate_url()

head()

stream()

checksum()

healthcheck()

Every backend must inherit from this interface.

====================================================
SUPPORTED STORAGE
====================================================

Create independent drivers for

Local

AWS S3

MinIO

Azure Blob

Google Cloud Storage

Cloudflare R2

Backblaze

Wasabi

DigitalOcean Spaces

Every driver must be isolated.

====================================================
ODOO INTEGRATION
====================================================

Integrate with

ir.attachment

without modifying Odoo core.

Use inheritance only.

Support

Binary fields

Attachment

Image fields

Reports

Documents

Mail attachments

Website media

Knowledge

Discuss

Portal

POS attachments

Any module using ir.attachment.

====================================================
UPLOAD FLOW
====================================================

User Upload

↓

Validation

↓

Virus Scan Hook

↓

Checksum

↓

Compression Hook

↓

Encryption Hook

↓

Storage Backend

↓

Metadata

↓

Database

====================================================
DOWNLOAD FLOW
====================================================

Attachment Request

↓

Permission Check

↓

Storage Backend

↓

Streaming Response

↓

Browser

Never download entire object into RAM.

Support HTTP Streaming.

====================================================
MULTIPART UPLOAD
====================================================

Automatically switch to multipart upload for configurable file size.

====================================================
PRESIGNED URL
====================================================

Support

GET

PUT

POST

DELETE

Temporary URLs

Expiration

====================================================
SECURITY
====================================================

Support

IAM Role

STS

Temporary Credentials

KMS Encryption

SSE-S3

SSE-KMS

SSE-C

Bucket Policies

Private Bucket

Object Lock

Versioning

MFA Delete

Checksum Validation

Audit Logging

No Access Keys stored in plaintext.

Secrets should support

Odoo Secret Store

Vault

AWS Secrets Manager

Azure Key Vault

====================================================
METADATA
====================================================

Store metadata separately.

Example

backend

bucket

container

region

endpoint

storage_class

object_key

etag

checksum

mime

size

created

modified

kms_key

version_id

====================================================
MULTI TENANT
====================================================

Support

Company

Database

Environment

Workspace

Prefix

Folder Strategy

No collision.

====================================================
DEDUPLICATION
====================================================

SHA256 based.

If identical object already exists

Reuse it.

Reference counting.

Garbage collector.

====================================================
CACHE
====================================================

Support optional

Redis

Filesystem Cache

CDN

CloudFront

Reverse Proxy

====================================================
ASYNC
====================================================

Background jobs

Migration

Copy

Delete

Checksum verification

Thumbnail generation

Image optimization

====================================================
MIGRATION
====================================================

Provide migration wizard

Filesystem

↓

S3

S3

↓

MinIO

MinIO

↓

Azure

Without downtime.

Rollback supported.

====================================================
OBSERVABILITY
====================================================

Prometheus metrics

OpenTelemetry

Structured Logging

Health Endpoint

Latency

Error Rate

Storage Usage

====================================================
CONFIGURATION
====================================================

Create UI under

Settings

Storage

Allow administrators to

Create storage backend

Enable backend

Disable backend

Test connection

Rotate credentials

Health check

Default backend

Per company backend

Per model backend

====================================================
ADMIN FEATURES
====================================================

Dashboard

Storage Usage

Object Count

Growth

Cost Estimation

Unused Objects

Broken References

Orphan Objects

====================================================
API
====================================================

Expose public service

storage.write()

storage.read()

storage.delete()

storage.generate_url()

Other modules must never use SDK directly.

====================================================
EXTENSIBILITY
====================================================

New storage providers should be installable without modifying existing code.

Plugin architecture.

====================================================
TESTING
====================================================

Unit Tests

Integration Tests

Performance Tests

Mock Storage

CI/CD

GitHub Actions

Coverage >95%

====================================================
DOCUMENTATION
====================================================

Generate

README

Architecture Diagram

Sequence Diagram

ERD

Developer Guide

Administrator Guide

Migration Guide

API Reference

====================================================
CODE QUALITY
====================================================

Use

PEP8

Type Hint

Docstring

Dependency Injection

SOLID

DRY

Clean Architecture

Hexagonal Architecture

Design Patterns where appropriate.

Avoid duplicated logic.

====================================================
OUTPUT
====================================================

Generate the project step-by-step.

Do NOT generate everything at once.

Phase 1

Project Architecture

Phase 2

Folder Structure

Phase 3

Base Storage Interface

Phase 4

Storage Registry

Phase 5

Driver Loader

Phase 6

Odoo Integration

Phase 7

AWS S3 Driver

Phase 8

MinIO Driver

...

Each phase must be reviewed before continuing.

Act like an experienced open-source maintainer writing an OCA-quality module intended for thousands of production deployments.