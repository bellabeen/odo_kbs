"""BackendRegistry — plugin discovery + instantiation (ADR-002, ADD §8).

Each provider module registers a factory here. Business logic asks the
registry for a backend by code ('s3', 'local', ...) and receives an
instance of `StorageBackend`. Registry is process-local and thread-safe.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, Optional

from ..exceptions import BackendNotFoundError, StorageConfigurationError
from ..interfaces import StorageBackend

_logger = logging.getLogger(__name__)

BackendFactory = Callable[[dict], StorageBackend]
"""Build a backend instance from config dict (credentials, region, ...)."""


class BackendRegistry:
    """Maps `backend_code` → factory. Lazy per-instance caching."""

    def __init__(self) -> None:
        self._factories: Dict[str, BackendFactory] = {}
        self._lock = threading.RLock()

    # ---------- registration ----------

    def register(self, code: str, factory: BackendFactory) -> None:
        """Idempotent registration. Latest factory wins on re-register."""
        if not code:
            raise StorageConfigurationError("backend code required")
        with self._lock:
            self._factories[code] = factory
            _logger.info(
                "storage backend registered",
                extra={"backend": code, "op": "register"},
            )

    def unregister(self, code: str) -> None:
        with self._lock:
            self._factories.pop(code, None)

    def codes(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._factories))

    # ---------- lookup ----------

    def has(self, code: str) -> bool:
        with self._lock:
            return code in self._factories

    def get(self, code: str, config: Optional[dict] = None) -> StorageBackend:
        """Instantiate backend for `code` using `config`.

        Raises BackendNotFoundError when unregistered.
        """
        with self._lock:
            factory = self._factories.get(code)
        if factory is None:
            raise BackendNotFoundError(
                f"storage backend '{code}' not registered",
                backend=code,
            )
        backend = factory(config or {})
        if backend.backend_code != code:
            # Defensive — factory lied about its code.
            raise StorageConfigurationError(
                f"factory for '{code}' built backend_code='{backend.backend_code}'",
                backend=code,
            )
        return backend


_default: Optional[BackendRegistry] = None
_default_lock = threading.RLock()


def get_default_registry() -> BackendRegistry:
    """Process-wide registry. Modules call `register()` on import."""
    global _default
    if _default is None:
        with _default_lock:
            if _default is None:
                _default = BackendRegistry()
    return _default
