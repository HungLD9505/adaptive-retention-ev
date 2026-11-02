"""Synthetic outcome-blind Final Drift derivation and receipt recovery."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from experiments.hung_sprint2.final_dispatch import _locked_drift_reference
from experiments.hung_sprint2.final_drift import derive_drift_reference
from tests.test_hung_final_role_replay import final_fixture

ROOT = Path(__file__).resolve().parents[1]
SPEC = {
    "schema": "hung-final-drift-reference-v1",
    "rule": "first_created_final_forecast_valid_load_population_sd",
    "scale_floor": 0.1,
}


class FinalDriftTests(unittest.TestCase):
    def test_no_label_read_and_immutable_resume(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            input_run, manifest_sha = final_fixture(root, days=3)
            job = {
                "job_id": "drift_fixture",
                "dataset_id": "urbanev",
                "city_id": "SZH",
                "entity_id": "dev-1",
                "input_run": str(input_run),
                "input_manifest_sha256": manifest_sha,
            }
            context = {
                "lock": {"drift_reference": SPEC},
                "output_root": root / "out",
                "lock_sha256": "a" * 64,
            }
            original = Path.open

            def no_labels(path: Path, *args: object, **kwargs: object):
                if path.name == "labels.jsonl":
                    raise AssertionError("Final labels were opened")
                return original(path, *args, **kwargs)

            with mock.patch.object(Path, "open", no_labels):
                first = _locked_drift_reference(context, job)
                self.assertEqual(first, _locked_drift_reference(context, job))
                self.assertEqual(first, derive_drift_reference(job, SPEC))
            self.assertGreaterEqual(first["scale"], 0.1)
            forecast = input_run / "forecasts.jsonl"
            with forecast.open("a", encoding="utf-8") as stream:
                stream.write("changed\n")
            with self.assertRaisesRegex(ValueError, "history changed"):
                _locked_drift_reference(context, job)

    def test_receipt_tamper_rejected_on_resume(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            input_run, manifest_sha = final_fixture(root, days=3)
            job = {
                "job_id": "drift_fixture",
                "dataset_id": "urbanev",
                "city_id": "SZH",
                "entity_id": "dev-1",
                "input_run": str(input_run),
                "input_manifest_sha256": manifest_sha,
            }
            context = {
                "lock": {"drift_reference": SPEC},
                "output_root": root / "out",
                "lock_sha256": "a" * 64,
            }
            _locked_drift_reference(context, job)
            manifest = (
                root / "out" / "stages" / "drift_fixture" / "drift_reference" / "run_manifest.json"
            )
            with manifest.open("a", encoding="utf-8") as stream:
                stream.write("tampered")
            with self.assertRaisesRegex(ValueError, "Receipt identity/output mismatch"):
                _locked_drift_reference(context, job)
