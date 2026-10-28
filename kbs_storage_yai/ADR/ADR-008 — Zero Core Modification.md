# ADR-008: Never Modify Odoo Core

Status: Accepted

## Context

Core modifications complicate upgrades.

## Decision

Use inheritance only.

No monkey patching.

No source modification.

## Consequences

Future compatibility.

Easy upgrades.

Marketplace friendly.