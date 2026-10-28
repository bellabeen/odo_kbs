# ADR-003: Separate Metadata from Binary Objects

Status: Accepted

## Context

Binary objects may reside in different storage providers.

Application metadata still needs transactional consistency.

## Decision

Store metadata inside PostgreSQL (ir.attachment).

Store binary objects inside object storage.

## Consequences

Advantages

Database remains authoritative.

Simple migration.

Easy reporting.

Rejected Alternatives

Store metadata inside object storage.