"""Backend discovery / loading / lifecycle (ADD §8, ADR-002)."""

from .backend_registry import BackendRegistry, get_default_registry

__all__ = ["BackendRegistry", "get_default_registry"]
