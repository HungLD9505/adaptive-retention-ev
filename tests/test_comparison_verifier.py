"""Independent minimal immutable-transaction fixtures for post-hoc checks."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verify_comparison import InputSnapshots, sha, verify_run


class ArtifactVerifierTests(unittest.TestCase):
    @staticmethod
    def origin_hash(origins):
        return hashlib.sha256(
            json.dumps(sorted(origins), separators=(",", ":")).encode()
        ).hexdigest()

    def complete_fixture(self, base):
        run, data = self.fixture(base)
        origin = "2023-07-01T00:00:00"
        schedule = {
            "identity": ["charged", "AMS", "0"],
            "role": "development",
            "origin": origin,
            "input_run_id": "identified-input",
            "status": "created",
        }
        (data / "schedule.jsonl").write_text(json.dumps(schedule) + "\n")
        manifest = json.loads((data / "manifest.json").read_text())
        manifest["run_id"] = "identified-input"
        manifest["config"] = {
            "dataset_id": "charged",
            "city_id": "AMS",
            "history_days": 7,
            "deployment": origin,
            "replay_stop": "2023-07-02T00:00:00",
            "availability_delay_hours": 0,
        }
        manifest["files"]["schedule.jsonl"] = {
            "sha256": sha(data / "schedule.jsonl"),
            "size_bytes": (data / "schedule.jsonl").stat().st_size,
        }
        (data / "manifest.json").write_text(json.dumps(manifest))
        last = run / "tick-0002"
        last.mkdir()
        (last / "forecasts.json").write_text("{}")
        (last / "events.jsonl").write_text("")
        (last / "state.pt").write_bytes(b"fixture-terminal")
        report = json.loads((run / "run.json").read_text())
        report["binding"]["schema"] = "ev-prequential-run-v1"
        report["binding"]["config"] = {"replay_days": 1, "state_retention": "all"}
        report["binding"]["input"].update(
            input_manifest_sha256=sha(data / "manifest.json"),
            input_run_id="identified-input",
            history_days=7,
        )
        report.update(
            scheduled_days=1,
            pending_days=0,
            ticks=3,
            issued_origins_sha256=self.origin_hash([origin]),
            scored_origins_sha256=self.origin_hash([origin]),
        )
        (run / "run.json").write_text(json.dumps(report))
        self.recommit(run)
        return run, data

    def test_complete_run_checks_terminal_schedule_and_due_score(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.complete_fixture(Path(temp))
            for cache in (None, InputSnapshots()):
                result = verify_run(run, data, input_snapshots=cache)
                self.assertEqual(result["scheduled_days"], 1)
                self.assertEqual(result["complete_labels_scored"], 1)

    def test_hash_consistent_truncated_run_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.complete_fixture(Path(temp))
            (run / "tick-0002").rename(run / "detached-terminal")
            report = json.loads((run / "run.json").read_text())
            report["ticks"] = 2
            (run / "run.json").write_text(json.dumps(report))
            self.recommit(run)
            with self.assertRaisesRegex(ValueError, "terminal daily tick"):
                verify_run(run, data)

    def test_hash_consistent_missing_due_score_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.complete_fixture(Path(temp))
            (run / "tick-0001/events.jsonl").write_text("")
            report = json.loads((run / "run.json").read_text())
            report.update(
                scored_days=0,
                scored_origins_sha256=self.origin_hash([]),
                active_mae_kwh=None,
                active_rmse_kwh=None,
            )
            (run / "run.json").write_text(json.dumps(report))
            self.recommit(run)
            with self.assertRaisesRegex(ValueError, "score event"):
                verify_run(run, data)

    def test_identified_schedule_cannot_disagree_with_forecast(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.complete_fixture(Path(temp))
            row = json.loads((data / "schedule.jsonl").read_text())
            row["status"] = "skipped_all_missing_history"
            (data / "schedule.jsonl").write_text(json.dumps(row) + "\n")
            manifest = json.loads((data / "manifest.json").read_text())
            manifest["files"]["schedule.jsonl"].update(
                sha256=sha(data / "schedule.jsonl"),
                size_bytes=(data / "schedule.jsonl").stat().st_size,
            )
            (data / "manifest.json").write_text(json.dumps(manifest))
            report = json.loads((run / "run.json").read_text())
            report["binding"]["input"]["input_manifest_sha256"] = sha(data / "manifest.json")
            (run / "run.json").write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "identified schedule"):
                verify_run(run, data, input_snapshots=InputSnapshots())

    def test_input_snapshot_reuse_preserves_proof_and_reads_label_bytes_once(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.audit_fixture(Path(temp))
            expected = verify_run(run, data)
            snapshots, reads = InputSnapshots(), []
            original = Path.read_bytes

            def read(path):
                if path == data.resolve() / "labels.jsonl":
                    reads.append(path)
                return original(path)

            with patch.object(Path, "read_bytes", autospec=True, side_effect=read):
                for _ in range(2):
                    self.assertEqual(verify_run(run, data, input_snapshots=snapshots), expected)
            identity = snapshots.identity()
            self.assertEqual(len(reads), 1)
            self.assertEqual(identity["sources"][0]["decoded_development_targets"], 1)
            self.assertEqual(
                identity["sources"][0]["files"]["labels.jsonl"]["sha256"],
                sha(data / "labels.jsonl"),
            )

    def test_input_snapshot_rejects_changed_files_and_manifest_request(self):
        for mode in ("label-file", "manifest-request"):
            with tempfile.TemporaryDirectory() as temp:
                run, data = self.audit_fixture(Path(temp))
                snapshots = InputSnapshots()
                verify_run(run, data, input_snapshots=snapshots)
                if mode == "label-file":
                    with (data / "labels.jsonl").open("ab") as stream:
                        stream.write(b"\n")
                else:
                    report = json.loads((run / "run.json").read_text())
                    report["binding"]["input"]["input_manifest_sha256"] = "unrelated"
                    (run / "run.json").write_text(json.dumps(report))
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    verify_run(run, data, input_snapshots=snapshots)

    def test_snapshot_change_during_daily_checks_fails_before_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.audit_fixture(Path(temp))
            changed = False

            def hash_with_change(path):
                nonlocal changed
                if path.name == "state.pt" and not changed:
                    changed = True
                    with (data / "labels.jsonl").open("ab") as stream:
                        stream.write(b"\n")
                return sha(path)

            with patch("tools.verify_comparison.sha", side_effect=hash_with_change):
                with self.assertRaisesRegex(ValueError, "snapshot files changed"):
                    verify_run(run, data, input_snapshots=InputSnapshots())

    def test_snapshot_does_not_decode_unselected_final_label_arrays(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp))
            # Deliberately non-JSON Final values expose accidental broad decoding.
            with (data / "labels.jsonl").open("ab") as stream:
                stream.write(
                    b'\n{"identity": ["charged", "AMS", "final"], "origin": "future", "energy_kwh": [NOT_JSON]}\n'
                )
            manifest = json.loads((data / "manifest.json").read_text())
            manifest["files"]["labels.jsonl"]["sha256"] = sha(data / "labels.jsonl")
            (data / "manifest.json").write_text(json.dumps(manifest))
            report = json.loads((run / "run.json").read_text())
            report["binding"]["input"]["input_manifest_sha256"] = sha(data / "manifest.json")
            (run / "run.json").write_text(json.dumps(report))
            self.assertEqual(
                verify_run(run, data, input_snapshots=InputSnapshots()), verify_run(run, data)
            )

    def test_snapshot_rejects_final_target_before_label_decoding(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.fixture(Path(temp), role="final")
            with self.assertRaisesRegex(ValueError, "only permits Development"):
                verify_run(run, data, input_snapshots=InputSnapshots())

    def audit_fixture(self, base):
        run, data = self.fixture(base)
        t0, t1 = run / "tick-0000", run / "tick-0001"
        forecast = json.loads((t0 / "forecasts.json").read_text())
        forecast.update(
            active=0.1,
            predictions=[[1.0] * 24] * 3,
            audit_origin={"start": forecast["origin"], "lambda": 0},
            audit_prediction=[0.5] * 24,
        )
        (t0 / "forecasts.json").write_text(json.dumps(forecast))
        event = json.loads((t1 / "events.jsonl").read_text())
        event.update(
            prediction_sha256=sha(t0 / "forecasts.json"),
            issued_active=0.1,
            mae_scaled=[0.8] * 3,
            mse_scaled=[0.64] * 3,
        )
        audit = {
            "event": "audit_summary",
            "switch": forecast["audit_origin"],
            "paired_days": 1,
            "mean_new_minus_old": 0.5,
            "daily": [{"origin": forecast["origin"], "new_minus_old": 0.5}],
        }
        (t1 / "events.jsonl").write_text(json.dumps(event) + "\n" + json.dumps(audit) + "\n")
        report = json.loads((run / "run.json").read_text())
        report.update(candidate_levels=[0, 0.1, 1], decisions=[], audits=[audit])
        (run / "run.json").write_text(json.dumps(report))
        self.recommit(run)
        return run, data

    def recommit(self, run):
        previous = "0" * 64
        for index, tick in enumerate(sorted(run.glob("tick-*"))):
            (tick / "commit.json").write_text(
                json.dumps(
                    {
                        "previous": previous,
                        "index": index,
                        "files": {
                            n: sha(tick / n) for n in ("forecasts.json", "events.jsonl", "state.pt")
                        },
                    }
                )
            )
            previous = sha(tick / "commit.json")
        report = json.loads((run / "run.json").read_text())
        report["commit_chain"] = previous
        (run / "run.json").write_text(json.dumps(report))

    def test_audit_original_unit_forecasts_are_recomputed_without_training(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.audit_fixture(Path(temp))
            result = verify_run(run, data)
            self.assertEqual(result["audit_summaries_verified"], 1)
            self.assertEqual(result["audit_forecast_scores_verified"], 1)

    def test_hash_consistent_false_audit_metric_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            run, data = self.audit_fixture(Path(temp))
            path = run / "tick-0001/events.jsonl"
            events = [json.loads(s) for s in path.read_text().splitlines()]
            events[-1].update(
                mean_new_minus_old=0.7,
                daily=[{"origin": "2023-07-01T00:00:00", "new_minus_old": 0.7}],
            )
            path.write_text("\n".join(json.dumps(e) for e in events))
            report = json.loads((run / "run.json").read_text())
            report["audits"] = [events[-1]]
            (run / "run.json").write_text(json.dumps(report))
            self.recommit(run)
            with self.assertRaisesRegex(ValueError, "Audit gap"):
                verify_run(run, data)

    def test_report_only_audit_or_decision_mutation_is_rejected(self):
        for name in ("audits", "decisions"):
            with tempfile.TemporaryDirectory() as temp:
                run, data = self.audit_fixture(Path(temp))
                report = json.loads((run / "run.json").read_text())
                report[name] = [] if name == "audits" else [{"selected_lambda": 99}]
                (run / "run.json").write_text(json.dumps(report))
                with (
                    self.subTest(name=name),
                    self.assertRaisesRegex(ValueError, "decisions/audits"),
                ):
                    verify_run(run, data)

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
