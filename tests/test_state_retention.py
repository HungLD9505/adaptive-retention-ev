"""Rolling checkpoint retention must not alter predictions, state or resume."""

import unittest
from unittest.mock import patch

import test_prequential_runner as fixtures

from ev_runner.state import state_digest

DAY = fixtures.DAY


class RetentionTests(unittest.TestCase):
    setUp = fixtures.RunnerTests.setUp
    tearDown = fixtures.RunnerTests.tearDown
    runner = fixtures.RunnerTests.runner

    def test_latest_matches_dense_and_resumes_exactly(self):
        self.binding["config"] = {"state_retention": "all"}
        dense = self.runner("dense")
        dense.run_until(self.replay.start + 6 * DAY)
        self.binding["config"] = {"state_retention": "latest"}
        compact = self.runner("compact")
        compact.run_until(self.replay.start + 2 * DAY)
        resumed = self.runner("resumed", self.root / "compact")
        resumed.run_until(self.replay.start + 6 * DAY)
        compact.run_until(self.replay.start + 6 * DAY)
        for name in ("compact", "resumed"):
            self.assertEqual(len(list((self.root / name).glob("tick-*/state.pt"))), 1)
            for tick in (self.root / "dense").glob("tick-*"):
                self.assertEqual(
                    (tick / "forecasts.json").read_bytes(),
                    (self.root / name / tick.name / "forecasts.json").read_bytes(),
                )
        self.assertEqual(
            state_digest({k: v for k, v in dense.snapshot().items() if k != "cost"}),
            state_digest({k: v for k, v in compact.snapshot().items() if k != "cost"}),
        )
        self.assertEqual(
            state_digest({k: v for k, v in resumed.snapshot().items() if k != "cost"}),
            state_digest({k: v for k, v in compact.snapshot().items() if k != "cost"}),
        )

    def test_latest_checkpoint_and_logs_are_mandatory(self):
        self.binding["config"] = {"state_retention": "latest"}
        r = self.runner()
        r.run_until(self.replay.start + 2 * DAY)
        last = self.root / "run/tick-0002/state.pt"
        saved = last.read_bytes()
        last.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.runner("missing-state", self.root / "run")
        last.write_bytes(saved)
        (self.root / "run/tick-0000/events.jsonl").write_text("changed")
        with self.assertRaises(ValueError):
            self.runner("bad-events", self.root / "run")

    def test_resume_policy_must_match_and_old_runs_are_not_compacted(self):
        r = self.runner()
        r.run_until(self.replay.start + 2 * DAY)
        self.assertEqual(len(list((self.root / "run").glob("tick-*/state.pt"))), 3)
        self.binding["config"] = {"state_retention": "latest"}
        with self.assertRaises(ValueError):
            self.runner("different-policy", self.root / "run")
        self.assertEqual(len(list((self.root / "run").glob("tick-*/state.pt"))), 3)

    def test_failed_commit_keeps_previous_checkpoint(self):
        self.binding["config"] = {"state_retention": "latest"}
        r = self.runner()
        r.run_until(self.replay.start)
        previous = self.root / "run/tick-0000/state.pt"
        with patch("ev_runner.store.os.replace", side_effect=OSError("injected failure")):
            with self.assertRaises(OSError):
                r.run_until(self.replay.start + DAY)
        self.assertTrue(previous.exists())
        with self.assertRaises(ValueError):
            self.runner("pending-fails", self.root / "run")


if __name__ == "__main__":
    unittest.main()
