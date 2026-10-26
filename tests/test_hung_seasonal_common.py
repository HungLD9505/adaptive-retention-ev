"""Proposed Seasonal Naive policy in Hung's durable Development replay."""

from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.cli import ARTIFACTS
from experiments.hung_sprint2.seasonal_naive import forecast_previous_day
from experiments.hung_sprint2.single_baseline import SingleBaselineRunner
from experiments.hung_sprint2.single_baseline_cli import _replay
from experiments.hung_sprint2.single_forecast_journal import verify_forecast_journal
from tests import test_hung_single_baseline as fixture


def seasonal_input(root: Path) -> tuple[Path, str]:
    run, _ = fixture.target_input(root)
    path = run / "forecasts.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        for hour in row["x_hist"]:
            hour[0], hour[6] = 0.4, 1.0
    # The masked filler is never an observed zero or an admissible prediction.
    rows[0]["x_hist"][5][0], rows[0]["x_hist"][5][6] = 999.0, 0.0
    rows[0]["x_hist"][23][0] = 0.6
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["forecasts.jsonl"]["sha256"] = sha256_file(path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return run, sha256_file(manifest_path)


class SeasonalCommonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_previous_day_and_last_observed_fallback_do_not_use_masked_filler(self) -> None:
        history = torch.zeros((24, 7))
        history[:, 0] = torch.arange(24)
        history[:, 6] = 1
        history[5, 0], history[5, 6] = 999, 0
        prediction = forecast_previous_day(history)
        self.assertEqual(prediction.fallback_hours, 1)
        self.assertEqual(prediction.scaled_kwh[5].item(), 23)
        self.assertEqual(prediction.scaled_kwh[4].item(), 4)
        self.assertEqual(history[5, 0].item(), 999)
        history[:, 6] = 0
        with self.assertRaisesRegex(ValueError, "All-missing"):
            forecast_previous_day(history)

    def test_common_replay_persists_forecast_score_cost_and_split_resume(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            run, digest = seasonal_input(root)
            first_args = fixture.replay_args(root, run, digest, "seasonal_naive", "first", 1)
            first = _replay(first_args)
            self.assertIsNone(first["metrics_kwh"])
            self.assertIsNone(first["initial_checkpoint_sha256"])
            self.assertIsNone(first["source_checkpoint_sha256"])
            resumed_args = deepcopy(first_args)
            resumed_args.output = root / "resumed"
            resumed_args.max_origins = 3
            resumed_args.resume_checkpoint = first_args.output / "runner.pt"
            resumed = _replay(resumed_args)
            direct_args = deepcopy(resumed_args)
            direct_args.output = root / "direct"
            direct_args.resume_checkpoint = None
            direct = _replay(direct_args)
            self.assertEqual(resumed["coverage"], direct["coverage"])
            self.assertEqual(resumed["metrics_kwh"], direct["metrics_kwh"])
            self.assertEqual(resumed["event_evidence"], direct["event_evidence"])
            self.assertEqual(resumed["cost"]["fallback_hours"], 1)
            self.assertEqual(resumed["cost"]["inference_calls"], 2)
            self.assertEqual(resumed["cost"]["candidate_count"], 1)
            self.assertEqual(resumed["cost"]["update_steps"], 0)
            self.assertEqual(resumed["model_tensor_bytes"], 0)
            self.assertEqual(resumed["model_optimizer_tensor_bytes"], 0)
            self.assertEqual(
                resumed["config"]["fallback_policy"], "previous_day_24h_last_observed_fallback"
            )
            records = verify_forecast_journal(
                resumed_args.output, run, resumed["input_binding"], resumed["code"]
            )
            self.assertEqual([record["fallback_hours"] for record in records], [1, 0, 0])
            self.assertAlmostEqual(records[0]["prediction"][5], 0.6)
            self.assertEqual(records[2]["prediction"], None)
            state = torch.load(resumed_args.output / "runner.pt", weights_only=True)
            self.assertIsNone(state["model"])
            self.assertIsNone(state["optimizer"])
            self.assertEqual(state["issued"][0]["fallback_hours"], 1)
            self.assertAlmostEqual(state["issued"][0]["mae_kwh"], 2 * 0.2 * 5 / 24)
            broken = deepcopy(state)
            broken["cost"]["fallback_hours"] = 0
            with self.assertRaisesRegex(ValueError, "cost accounting"):
                SingleBaselineRunner.from_state_dict(
                    broken, expected_binding=resumed["input_binding"]
                )
            journal_path = resumed_args.output / "forecasts.jsonl"
            journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
            journal[1]["fallback_hours"] = 0
            journal_path.write_text(
                "".join(json.dumps(row) + "\n" for row in journal), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "Issued forecast was changed"):
                verify_forecast_journal(
                    resumed_args.output, run, resumed["input_binding"], resumed["code"]
                )

    def test_proposed_rule_rejects_source_or_model_inputs_and_is_issued_before_label(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            run, digest = seasonal_input(root)
            args = fixture.replay_args(root, run, digest, "seasonal_naive", "bad", 3)
            args.source_manifest_sha256 = "a" * 64
            with self.assertRaisesRegex(ValueError, "no checkpoint/Source"):
                _replay(args)
            self.assertFalse(args.output.exists())
            args.source_manifest_sha256 = None

            from experiments.hung_sprint2 import replay_inputs

            def crash_before_label(*_args, **_kwargs):
                journal = args.output / "forecasts.jsonl"
                records = [json.loads(line) for line in journal.read_text().splitlines()]
                self.assertEqual(records[1]["fallback_hours"], 1)
                self.assertAlmostEqual(records[1]["prediction"][5], 0.6)
                self.assertTrue((args.output / records[1]["checkpoint"]).exists())
                raise RuntimeError("label-read crash")

            with patch.object(replay_inputs, "_label_record", side_effect=crash_before_label):
                with self.assertRaisesRegex(RuntimeError, "label-read crash"):
                    _replay(args)
            self.assertFalse((args.output / "run_manifest.json").exists())
            journal = [
                json.loads(line)
                for line in (args.output / "forecasts.jsonl").read_text().splitlines()
            ]
            restart = deepcopy(args)
            restart.output = root / "restart"
            restart.resume_checkpoint = args.output / journal[-1]["checkpoint"]
            completed = _replay(restart)
            self.assertEqual(completed["coverage"]["requested"], 3)
            self.assertEqual(completed["cost"]["fallback_hours"], 1)

    def test_final_payload_is_not_decoded_or_used_for_development_forecasts(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            results = []
            for folder, poison in (("plain", False), ("final-poison", True)):
                parent = root / folder
                parent.mkdir()
                run, digest = seasonal_input(parent)
                if poison:
                    for name, record in (
                        (
                            "forecasts.jsonl",
                            '{"role": "final", "identity": ["urbanev", "SZH", "other"], "x_hist": BROKEN}\n',
                        ),
                        (
                            "labels.jsonl",
                            '{"role": "final", "identity": ["urbanev", "SZH", "other"], "energy_kwh": BROKEN}\n',
                        ),
                    ):
                        with (run / name).open("a", encoding="utf-8") as stream:
                            stream.write(record)
                    manifest_path = run / "manifest.json"
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest["files"] = {
                        name: {"sha256": sha256_file(run / name)} for name in ARTIFACTS
                    }
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    digest = sha256_file(manifest_path)
                args = fixture.replay_args(parent, run, digest, "seasonal_naive", "result", 3)
                result = _replay(args)
                records = verify_forecast_journal(
                    args.output, run, result["input_binding"], result["code"]
                )
                results.append((result["metrics_kwh"], [r["prediction"] for r in records]))
            self.assertEqual(results[0], results[1])


if __name__ == "__main__":
    unittest.main()
