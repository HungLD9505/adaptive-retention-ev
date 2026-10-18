"""Proposed entity roles independent of energy values and other cohort members."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

SplitRole = Literal["source", "development", "final"]
SPLIT_POLICY = "entity-sha256-threshold-v1"


def entity_role(dataset_id: str, city_id: str, entity_id: str, *, salt: str) -> SplitRole:
    """Assign a role with approximate 60/20/20 proportions, not exact cohort quotas.

    Identity strings are preserved, including leading zeros. The caller supplies a
    recorded, predeclared salt; it must never be searched using final outcomes.
    This separates identifiers, not physical sites with duplicate/co-located IDs.
    """
    identity = (dataset_id, city_id, entity_id, salt)
    if any(not isinstance(value, str) or not value.strip() for value in identity):
        raise ValueError("Dataset, city, entity and salt must be nonempty strings")
    payload = json.dumps(
        [SPLIT_POLICY, *identity], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    number = int.from_bytes(hashlib.sha256(payload).digest(), "big")
    # Integer thresholds avoid platform-dependent floating point bucket boundaries.
    if number * 5 < (1 << 256) * 3:
        return "source"
    if number * 5 < (1 << 256) * 4:
        return "development"
    return "final"
