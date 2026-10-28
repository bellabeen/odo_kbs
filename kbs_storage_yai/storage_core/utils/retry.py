"""Exponential-backoff retry decorator (ADD §13).

Circuit breaker and graceful degradation live at service layer — out of
scope here. This util is intentionally tiny; callers own classification.
"""

from __future__ import annotations

import functools
import logging
import random
import time
from typing import Any, Callable, Tuple, Type, TypeVar

_logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    *,
    attempts: int = 3,
    backoff: float = 0.5,
    max_backoff: float = 8.0,
    retryable: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Retry `retryable` exceptions with exponential backoff + jitter.

    Non-retryable exceptions propagate immediately.
    """

    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = backoff
            last: BaseException | None = None
            for i in range(attempts):
                try:
                    return func(*args, **kwargs)
                except retryable as err:
                    last = err
                    if i == attempts - 1:
                        raise
                    _logger.warning(
                        "retrying after error",
                        extra={
                            "func": func.__qualname__,
                            "attempt": i + 1,
                            "err": repr(err),
                        },
                    )
                    time.sleep(delay + random.uniform(0, delay))
                    delay = min(delay * 2, max_backoff)
            assert last is not None
            raise last  # pragma: no cover — unreachable

        return wrapper  # type: ignore[return-value]

    return decorator
