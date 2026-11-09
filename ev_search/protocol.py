"""Exact issue #99 scored-protocol configuration and code bindings."""

import hashlib
import re

from ev_runner.continuous_run import code_identity
from ev_search.ledger import canonical


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def require_scored_bindings(
    protocol: dict,
    study_template: dict,
    *,
    fixed_search_config_sha256: str,
    phase: str,
) -> None:
    """Match search bytes, the phase-specific canonical study, and code commit."""
    if phase not in {"calibration", "evaluation"} or study_template.get("phase") != phase:
        raise ValueError("Scored study phase differs from requested protocol binding")
    if protocol.get("status") != "locked_owner_approved" or not protocol.get("owner_authorization"):
        raise ValueError("Scored search requires owner-locked authorized protocol")
    search_sha = protocol.get("fixed_search_config_sha256")
    calibration_sha = protocol.get("calibration_study_template_sha256")
    evaluation_sha = protocol.get("evaluation_study_template_sha256")
    study_sha = calibration_sha if phase == "calibration" else evaluation_sha
    commit = protocol.get("code_commit")
    if not all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (search_sha, calibration_sha, evaluation_sha)
    ):
        raise ValueError(
            "Protocol needs 64-hex fixed-search file and both canonical study SHA-256 bindings"
        )
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Protocol needs exact 40-hex code_commit")
    if search_sha != fixed_search_config_sha256:
        raise ValueError("Fixed search JSON file SHA-256 differs from locked protocol")
    if study_sha != canonical_sha256(study_template):
        raise ValueError(f"Canonical {phase} study template SHA-256 differs from locked protocol")
    if commit != code_identity()["commit"]:
        raise ValueError("Code commit differs from locked protocol")
