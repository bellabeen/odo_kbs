# ADR-002: Adopt Plugin-Based Storage Providers

Status: Accepted

## Context

Supporting multiple storage providers in a single module would create
large conditional blocks and increase maintenance complexity.

## Decision

Each provider SHALL be implemented as an independent Odoo module.

Example

storage_s3

storage_minio

storage_gcs

storage_r2

## Consequences

Advantages

Independent releases

Smaller dependencies

Optional installation

Easy contribution

Rejected Alternatives

Single monolithic module