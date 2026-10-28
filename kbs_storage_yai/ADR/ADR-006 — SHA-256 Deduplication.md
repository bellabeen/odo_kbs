# ADR-006: Deduplicate Objects Using SHA-256

Status: Accepted

## Context

Many organizations upload duplicate documents.

## Decision

Generate SHA-256 checksum.

Reuse identical objects.

Maintain reference count.

## Consequences

Storage cost reduction.

Smaller backup.

Trade-off

Extra checksum computation.