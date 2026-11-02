"""Downloaded-state checks detect committed-byte and model/RNG content changes."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

import torch

from ev_models.checkpoint import digest, write_json
from ev_runner.state import state_digest
from tools.verify_latest_states import verify_state


class LatestStateTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict, dict]:
        tick = root / "tick-0000"
        tick.mkdir()
        value = {
            "branches": {
                0.0: {
                    "model": {"weight": torch.tensor([1.0, 2.0])},
                    "optimizer": {"step": 3},
                    "rng": torch.tensor([4, 5], dtype=torch.uint8),
                }
            }
        }
        torch.save(value, tick / "state.pt")
        write_json(tick / "commit.json", {"files": {"state.pt": digest(tick / "state.pt")}})
        return value, {
            "run_id": "fixture",
            "ticks": 1,
            "commit_chain": digest(tick / "commit.json"),
            "final_branch_state_sha256": {"0.0": state_digest(value["branches"][0.0])},
        }

    def test_valid_cpu_contents_include_optimizer_and_rng(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, row = self.fixture(root)
            result = verify_state(root, row)
            self.assertEqual(result["branches"], row["final_branch_state_sha256"])

    def test_missing_ticks_bytes_commit_and_branch_contents_fail(self):
        for change in ("ticks", "bytes", "commit", "model", "optimizer", "rng"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                value, row = self.fixture(root)
                path = root / "tick-0000/state.pt"
                if change == "ticks":
                    row["ticks"] = 2
                elif change == "bytes":
                    path.write_bytes(b"corrupted")
                elif change == "commit":
                    row["commit_chain"] = "0" * 64
                else:
                    changed = copy.deepcopy(value)
                    changed["branches"][0.0][change] = {"changed": torch.tensor([99])}
                    torch.save(changed, path)
                    commit = root / "tick-0000/commit.json"
                    commit.write_text(json.dumps({"files": {"state.pt": digest(path)}}))
                    row["commit_chain"] = digest(commit)
                with self.assertRaises(ValueError):
                    verify_state(root, row)
