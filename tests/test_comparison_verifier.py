"""Independent minimal immutable-transaction fixtures for post-hoc checks."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.verify_comparison import sha, verify_run


class ArtifactVerifierTests(unittest.TestCase):
    def test_declared_latest_policy_accounts_for_missing_historical_state(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp))
            report = json.loads((run / "run.json").read_text())
            report["binding"]["config"] = {"state_retention": "latest"}
            (run / "run.json").write_text(json.dumps(report))
            (run / "tick-0000/state.pt").unlink()
            result = verify_run(run, data)
            self.assertEqual(result["files_hashed"], 5)
            self.assertEqual(result["historical_states_intentionally_omitted"], 1)
            (run / "tick-0001/state.pt").unlink()
            with self.assertRaises((ValueError, FileNotFoundError)):
                verify_run(run, data)

    def test_undeclared_missing_state_is_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp))
            (run / "tick-0000/state.pt").unlink()
            with self.assertRaises((ValueError, FileNotFoundError)):
                verify_run(run, data)

    def fixture(
        self,
        base: Path,
        *,
        role="development",
        arrival="2023-07-02T00:00:00",
        metric=8.0,
        leak=False,
    ):
        data, run = base / "data", base / "run"
        data.mkdir()
        run.mkdir()
        identity = ["charged", "AMS", "0"]
        origin = "2023-07-01T00:00:00"

        def write(path, value):
            path.write_text(json.dumps(value))

        write(
            data / "entities.jsonl",
            {"identity": identity, "role": role, "scale": {"energy_scale": 10}},
        )
        write(
            data / "labels.jsonl",
            {
                "identity": identity,
                "origin": origin,
                "energy_kwh": [2] * 24,
                "file_valid": [1] * 24,
                "available_at": [arrival] * 24,
            },
        )
        write(
            data / "manifest.json",
            {
                "files": {
                    name: {"sha256": sha(data / name)}
                    for name in ("entities.jsonl", "labels.jsonl")
                }
            },
        )
        t0 = run / "tick-0000"
        t0.mkdir()
        record = {"identity": identity}
        if leak:
            record["y_scaled"] = [0] * 24
        write(
            t0 / "forecasts.json",
            {"origin": origin, "active": 0.0, "predictions": [[1.0] * 24], "record": record},
        )
        (t0 / "events.jsonl").write_text("")
        (t0 / "state.pt").write_bytes(b"independent-fixture-no-pickle")
        write(
            t0 / "commit.json",
            {
                "previous": "0" * 64,
                "index": 0,
                "files": {n: sha(t0 / n) for n in ("forecasts.json", "events.jsonl", "state.pt")},
            },
        )
        t1 = run / "tick-0001"
        t1.mkdir()
        write(t1 / "forecasts.json", {})
        write(
            t1 / "events.jsonl",
            {
                "event": "score",
                "origin": origin,
                "as_of": "2023-07-02T00:00:00",
                "prediction_sha256": sha(t0 / "forecasts.json"),
                "issued_active": 0.0,
                "mae_scaled": [metric / 10],
                "mse_scaled": [0.64],
            },
        )
        (t1 / "state.pt").write_bytes(b"fixture-final")
        write(
            t1 / "commit.json",
            {
                "previous": sha(t0 / "commit.json"),
                "index": 1,
                "files": {n: sha(t1 / n) for n in ("forecasts.json", "events.jsonl", "state.pt")},
            },
        )
        write(
            run / "run.json",
            {
                "binding": {
                    "input": {
                        "dataset_id": "charged",
                        "city_id": "AMS",
                        "entity_id": "0",
                        "input_manifest_sha256": sha(data / "manifest.json"),
                    }
                },
                "candidate_levels": [0.0],
                "commit_chain": sha(t1 / "commit.json"),
                "issued_days": 1,
                "scored_days": 1,
                "active_mae_kwh": 8.0,
                "active_rmse_kwh": 8.0,
            },
        )
        return run, data

    def test_recomputes_original_units_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp))
            result = verify_run(run, data)
            self.assertEqual(result["files_hashed"], 6)
            self.assertEqual((result["mae_kwh"], result["rmse_kwh"]), (8, 8))

    def test_mutated_state_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp))
            (run / "tick-0000/state.pt").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_run(run, data)

    def test_final_role_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp), role="final")
            with self.assertRaises(ValueError):
                verify_run(run, data)

    def test_future_labels_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp), arrival="2023-07-03T00:00:00")
            with self.assertRaises(ValueError):
                verify_run(run, data)

    def test_saved_metric_disagrees_with_predictions(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp), metric=9)
            with self.assertRaises(ValueError):
                verify_run(run, data)

    def test_predictor_labels_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp), leak=True)
            with self.assertRaises(ValueError):
                verify_run(run, data)


if __name__ == "__main__":
    unittest.main()
