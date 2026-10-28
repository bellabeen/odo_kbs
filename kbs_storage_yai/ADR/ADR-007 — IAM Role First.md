# ADR-007: Prefer IAM Roles Over Static Credentials

Status: Accepted

## Context

Static access keys are difficult to rotate and increase security risks.

## Decision

Use IAM Roles whenever supported.

Fallback to Access Keys only when required.

## Consequences

Improved security.

Automatic credential rotation.

Least privilege.

Rejected Alternatives

Hardcoded credentials.