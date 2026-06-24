"""Privacy helpers for research exports."""

from __future__ import annotations

import hashlib
from typing import Optional


def hash_identifier(value: Optional[str], salt: str = "") -> str:
    """Return a SHA-256 hash for an identifier, or an empty string for blanks."""

    if not value:
        return ""
    normalized = f"{salt}:{value}".encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()
