"""SHA-256 helpers (ADR-006).

Stream-oriented so large payloads never load fully into RAM (ADR-004).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO, Iterator, Union

CHUNK_SIZE = 64 * 1024


def sha256_bytes(data: bytes) -> str:
    """Hex digest of in-memory payload."""
    return hashlib.sha256(data).hexdigest()


def sha256_stream(stream: Union[BinaryIO, Iterator[bytes]]) -> str:
    """Hex digest of chunked payload.

    Accepts a file-like object or iterator of bytes. Caller retains
    ownership — caller must rewind/reopen if they need to consume again.
    """
    h = hashlib.sha256()
    if hasattr(stream, "read"):
        while True:
            block = stream.read(CHUNK_SIZE)  # type: ignore[union-attr]
            if not block:
                break
            h.update(block)
    else:
        for block in stream:  # type: ignore[union-attr]
            h.update(block)
    return h.hexdigest()


def sha256_file(path: Union[str, Path]) -> str:
    """Hex digest of on-disk file, read in chunks."""
    with open(path, "rb") as fh:
        return sha256_stream(fh)
