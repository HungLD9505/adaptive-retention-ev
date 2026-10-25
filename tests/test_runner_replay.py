"""Use independent #18 producer fixtures to verify the delayed-label adapter."""

import unittest
from unittest.mock import patch

import test_input_loader as fixtures

from ev_inputs.loader import MISSING_DATA_POLICY
from ev_models.checkpoint import digest
from ev_models.data import InputRun
from ev_runner.engine import DAY
from ev_runner.replay import Replay


class ReplayTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.LoaderTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.run_loader("inputs", missing_data_policy=MISSING_DATA_POLICY)
        root = fixture.root / "inputs"
        self.inputs = InputRun(root, digest(root / "manifest.json"))

    def test_identity_clock_labels_and_forecast_are_separate(self):
        replay = Replay(self.inputs, "005", 2)
        record = replay.forecast(replay.start)
        self.assertNotIn("y_scaled", record)
        self.assertNotIn("energy_kwh", record)
        labels = replay.labels(replay.start, replay.start + DAY)
        self.assertEqual(labels.status, "complete")
        self.assertEqual(len(labels.values), 24)
        self.assertEqual(tuple(record["identity"]), replay.identity)

    def test_future_labels_are_not_opened(self):
        replay = Replay(self.inputs, "005", 2)
        with patch("pathlib.Path.open", side_effect=AssertionError("Future labels opened")):
            outcome = replay.labels(replay.start, replay.start)
        self.assertEqual(outcome.status, "pending")
        self.assertIsNone(outcome.values)

    def test_final_source_and_outside_horizon_fail(self):
        for entity in ("001", "003"):
            if (
                self.inputs.entities.get((*self.inputs.namespace, entity), {}).get("role")
                != "development"
            ):
                with self.assertRaisesRegex(ValueError, "Development"):
                    Replay(self.inputs, entity, 2)
        with self.assertRaisesRegex(ValueError, "horizon"):
            Replay(self.inputs, "005", 10000)

    def test_changed_label_file_rejected_before_replay(self):
        path = self.inputs.root / "labels.jsonl"
        path.write_text(path.read_text() + "{}\n")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            Replay(self.inputs, "005", 2)
