"""Offline guard tests for the contingent Block7 replay ledger."""

import tempfile
import unittest
from pathlib import Path

from tools.hung_block7_replay_preflight import (
    ROOT,
    assert_only_block_days_changes,
    replay_id,
    safe_payload_path,
)


class Block7ReplayPreflightTests(unittest.TestCase):
    def test_config_accepts_only_block_days_change(self) -> None:
        main = {"replay": {"block_days": 14, "max_origins": 90}, "seed": 11}
        block7 = {"replay": {"block_days": 7, "max_origins": 90}, "seed": 11}
        assert_only_block_days_changes(main, block7)
        block7["seed"] = 12
        with self.assertRaisesRegex(ValueError, "beyond"):
            assert_only_block_days_changes(main, block7)

    def test_replay_id_uses_distinct_namespace(self) -> None:
        self.assertEqual(replay_id("b14s11e1025"), "block7_replay_candidate_v1_b14s11e1025")
        with self.assertRaisesRegex(ValueError, "Invalid"):
            replay_id("../other")

    def test_payload_path_cannot_escape(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            self.assertEqual(safe_payload_path(root, "states/target.pt"), root / "states/target.pt")
            with self.assertRaisesRegex(ValueError, "escapes"):
                safe_payload_path(root, "../outside.pt")


if __name__ == "__main__":
    unittest.main()
