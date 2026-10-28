# ADR-004: Use Streaming Download

Status: Accepted

## Context

Large attachments should not be fully downloaded into memory.

## Decision

All download operations SHALL use streaming.

## Consequences

Advantages

Lower memory usage.

Better scalability.

Improved performance.

Rejected Alternatives

Temporary local files.

Read entire object into RAM.