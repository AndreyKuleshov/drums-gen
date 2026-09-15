"""Business logic for pattern ratings: hashing, upsert/delete, admin queries."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def content_hash(pattern: dict[str, Any]) -> str:
    """Stable sha256 of a pattern's content, independent of dict key order."""
    canonical = json.dumps(pattern, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
