# ADR-005: Binary Objects Are Immutable

Status: Accepted

## Context

Object storage is optimized for immutable objects.

## Decision

Objects SHALL never be modified.

Updates create new objects.

Old objects are garbage collected.

## Consequences

Simpler consistency.

Supports versioning.

Better auditing.