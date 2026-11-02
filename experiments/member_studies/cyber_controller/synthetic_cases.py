"""Synthetic generators for offline unit testing of the Adaptive Retention Controller.

Follows Acceptance Criteria 4:
- Deterministic streams and calculable cases.
- Insufficient days (B < B_min).
- Equality / keep (no switch).
- Clear single challenger switch.
- Two qualifying challengers with tie-breaking (largest LCB, nearest lambda, fixed order).
- Transitions to/from lambda = 0.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np


def generate_insufficient_days_case(
    active_id: str = "cand_low",
    b_valid: int = 5,
    b_missing: int = 9,
) -> List[Dict[str, any]]:
    """Generate block with fewer valid days than B_min, with large apparent challenger gains."""
    records = []
    # Valid days with strong challenger improvement
    for day in range(b_valid):
        records.append(
            {
                "day_index": day,
                "is_valid_day": True,
                "candidate_maes": {
                    active_id: 0.35,
                    "cand_0": 0.20,
                    "cand_high": 0.20,
                },
            }
        )
    # Missing / incomplete days
    for day in range(b_valid, b_valid + b_missing):
        records.append(
            {
                "day_index": day,
                "is_valid_day": False,
                "candidate_maes": {
                    active_id: 0.35,
                    "cand_0": 0.20,
                    "cand_high": 0.20,
                },
            }
        )
    return records


def generate_equality_keep_case(
    active_id: str = "cand_low",
    b_total: int = 14,
) -> List[Dict[str, any]]:
    """Generate block where all candidates have identical errors (or active is slightly better)."""
    records = []
    for day in range(b_total):
        records.append(
            {
                "day_index": day,
                "is_valid_day": True,
                "candidate_maes": {
                    active_id: 0.25,
                    "cand_0": 0.25,
                    "cand_high": 0.26,
                },
            }
        )
    return records


def generate_single_switch_case(
    active_id: str = "cand_low",
    target_winner_id: str = "cand_high",
    b_total: int = 14,
    seed: int = 101,
) -> List[Dict[str, any]]:
    """Generate block where target_winner has consistently lower error (LCB > delta)."""
    rng = np.random.default_rng(seed)
    records = []
    for day in range(b_total):
        base_err = 0.30 + float(rng.uniform(-0.02, 0.02))
        winner_err = base_err - 0.08 + float(rng.uniform(-0.01, 0.01))
        other_err = base_err + 0.05 + float(rng.uniform(-0.01, 0.01))

        other_id = "cand_0" if target_winner_id != "cand_0" else "cand_high"
        records.append(
            {
                "day_index": day,
                "is_valid_day": True,
                "candidate_maes": {
                    active_id: base_err,
                    target_winner_id: winner_err,
                    other_id: other_err,
                },
            }
        )
    return records


def generate_two_challengers_case(
    active_id: str = "cand_low",
    mode: str = "clear_lcb",  # "clear_lcb", "tie_nearest_lambda", "tie_fixed_order"
    b_total: int = 14,
) -> List[Dict[str, any]]:
    """Generate block where both challengers beat active, testing tie-breaking rules."""
    records = []
    for day in range(b_total):
        if mode == "clear_lcb":
            # cand_high beats active by 0.10, cand_0 beats active by 0.04
            records.append(
                {
                    "day_index": day,
                    "is_valid_day": True,
                    "candidate_maes": {
                        active_id: 0.30,
                        "cand_high": 0.20,
                        "cand_0": 0.26,
                    },
                }
            )
        elif mode == "tie_nearest_lambda":
            # Active is cand_low (0.1).
            # cand_0 (0.0) distance is 0.1; cand_high (1.0) distance is 0.9.
            # Both challengers beat active by exactly 0.06 every day -> identical LCB.
            records.append(
                {
                    "day_index": day,
                    "is_valid_day": True,
                    "candidate_maes": {
                        active_id: 0.30,
                        "cand_0": 0.24,
                        "cand_high": 0.24,
                    },
                }
            )
        elif mode == "tie_fixed_order":
            # Handled with custom lambda values where distances are equidistant
            records.append(
                {
                    "day_index": day,
                    "is_valid_day": True,
                    "candidate_maes": {
                        active_id: 0.30,
                        "cand_0": 0.24,
                        "cand_high": 0.24,
                    },
                }
            )
    return records
