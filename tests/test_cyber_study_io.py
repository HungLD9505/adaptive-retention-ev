"""Independent regressions for study forecast/availability and no-overwrite boundaries."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch

from ev_runner.replay import Labels
from experiments.member_studies.cyber_controller.model import EVForecasterGRU
from experiments.member_studies.cyber_controller.study_data import open_inputs
from experiments.member_studies.cyber_controller.study_runner import run_target_replay_study


class CyberStudyIOTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "forecasts.jsonl"
        self.start = datetime.fromisoformat("2022-12-01T00:00:00+08:00")
        self.replay = SimpleNamespace(
            start=self.start,
            stop=self.start + timedelta(days=2),
            delay=timedelta(0),
            inputs=None,
            scale=2.0,
            forecast=lambda origin: {
                "x_hist": [[0.0] * 6 + [1.0]] * 24,
                "c_future": [[0.0] * 5] * 24,
            },
        )
        self.source = EVForecasterGRU()

    def run_study(self):
        return run_target_replay_study(
            self.source,
            torch.ones(64),
            self.replay,
            7,
            ["urbanev", "SZH", "test"],
            forecast_path=self.path,
            block_size=2,
            b_min=1,
        )

    def test_predictions_are_on_disk_before_labels_and_incomplete_days_never_update(self):
        def labels(origin, as_of):
            self.assertEqual(as_of, origin + timedelta(days=1))
            records = [json.loads(x) for x in self.path.read_text().splitlines()]
            self.assertEqual(records[-1]["origin"], origin.isoformat())
            self.assertEqual(
                set(records[-1]["predictions_scaled"]), {"cand_0", "cand_low", "cand_high"}
            )
            if origin == self.start:
                return Labels("complete", (2.0,) * 24, as_of)
            return Labels("incomplete", None, as_of)

        self.replay.labels = labels
        with patch(
            "experiments.member_studies.cyber_controller.study_runner.TargetCandidate.update_on_day",
            return_value=0.0,
        ) as update:
            result = self.run_study()
        self.assertEqual(update.call_count, 3)
        self.assertEqual(result["runtime_metrics"]["total_update_steps"], 3)
        self.assertTrue(torch.equal(update.call_args.args[2], torch.ones(1, 24)))
        self.assertEqual(result["daily_records_count"], 2)
        self.assertFalse(result["daily_records"][1]["is_valid"])

    def test_pending_labels_fail_closed_before_any_update(self):
        self.replay.labels = lambda origin, clock: Labels(
            "pending", None, clock + timedelta(hours=1)
        )
        with patch(
            "experiments.member_studies.cyber_controller.study_runner.TargetCandidate.update_on_day"
        ) as update:
            with self.assertRaisesRegex(ValueError, "not yet available"):
                self.run_study()
            update.assert_not_called()
        self.assertEqual(len(self.path.read_text().splitlines()), 1)

    def test_nonfinite_complete_labels_are_rejected(self):
        self.replay.labels = lambda origin, clock: Labels("complete", (float("inf"),) * 24, clock)
        with self.assertRaisesRegex(ValueError, "Invalid arrived"):
            self.run_study()

    def test_existing_output_is_preserved_before_initial_adaptation(self):
        self.path.write_bytes(b"immutable existing evidence")
        self.replay.inputs = object()
        with patch(
            "experiments.member_studies.cyber_controller.study_runner.load_initial_target_samples"
        ) as initial:
            with self.assertRaises(FileExistsError):
                self.run_study()
            initial.assert_not_called()
        self.assertEqual(self.path.read_bytes(), b"immutable existing evidence")

    def test_nonzero_delay_is_explicitly_unsupported_in_this_bounded_study(self):
        self.replay.delay = timedelta(hours=1)
        with self.assertRaisesRegex(ValueError, "zero configured label delay"):
            self.run_study()
        self.assertFalse(self.path.exists())

    def test_partial_block_is_rejected_instead_of_silently_dropped(self):
        self.replay.stop += timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "complete calendar blocks"):
            self.run_study()

    def test_manifest_pin_is_required_and_actual_bytes_checked(self):
        root = Path(self.temp.name)
        (root / "manifest.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "explicit SHA-256"):
            open_inputs(root, "")
        with self.assertRaisesRegex(ValueError, "manifest SHA-256 mismatch"):
            open_inputs(root, "0" * 64)
