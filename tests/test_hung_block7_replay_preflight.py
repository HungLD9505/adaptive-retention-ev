"""Offline guard tests for the contingent Block7 replay ledger."""

import pytest

from tools.hung_block7_replay_preflight import (
    assert_only_block_days_changes,
    replay_id,
    safe_payload_path,
)


def test_config_accepts_only_block_days_change() -> None:
    main = {"replay": {"block_days": 14, "max_origins": 90}, "seed": 11}
    block7 = {"replay": {"block_days": 7, "max_origins": 90}, "seed": 11}
    assert_only_block_days_changes(main, block7)
    block7["seed"] = 12
    with pytest.raises(ValueError, match="beyond"):
        assert_only_block_days_changes(main, block7)


def test_replay_id_uses_distinct_namespace() -> None:
    assert replay_id("b14s11e1025") == "block7_replay_candidate_v1_b14s11e1025"
    with pytest.raises(ValueError, match="Invalid"):
        replay_id("../other")


def test_payload_path_cannot_escape(tmp_path) -> None:
    assert safe_payload_path(tmp_path, "states/target.pt") == tmp_path / "states/target.pt"
    with pytest.raises(ValueError, match="escapes"):
        safe_payload_path(tmp_path, "../outside.pt")
