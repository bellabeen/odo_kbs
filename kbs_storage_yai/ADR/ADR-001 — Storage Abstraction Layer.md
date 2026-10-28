# ADR-001: Introduce Storage Abstraction Layer (SAL)

Status: Accepted

## Context

Odoo stores binary files directly on a local or POSIX-compatible filesystem.
This tightly couples the application to a specific storage implementation and
makes migration to cloud object storage difficult.

Direct integration with cloud SDKs (e.g., boto3) inside business logic would
increase coupling and reduce maintainability.

## Decision

Introduce a Storage Abstraction Layer (SAL) that defines a common interface
for all storage providers.

The application layer interacts only with the abstraction.

Every provider (S3, MinIO, Azure Blob, GCS, etc.) implements the same interface.

## Consequences

Advantages

- Provider agnostic
- Easy to extend
- Easier testing
- Reduced coupling
- Better maintainability

Trade-offs

- Slightly more abstraction
- Additional implementation effort

Rejected Alternatives

- Direct boto3 integration
- Hardcoded provider logic