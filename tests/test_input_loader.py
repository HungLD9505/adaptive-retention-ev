"""Tiny independently authored producer-format files, never downloaded datasets."""

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ev_inputs.hourly_reader import read_source
from ev_inputs.loader import iter_forecasts, run_inputs

HEADER = [
    "dataset_id",
    "city_id",
    "entity_id",
    "timestamp",
    "energy_kwh",
    "file_valid_mask",
    "valid_sample_count",
    "expected_sample_count",
    "qc_flags",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.make_source()

    def make_source(self, *, dataset="charged", city="AMS", entity_major=False):
        self.dataset, self.city = dataset, city
        self.producer = self.root / f"producer-{dataset}-{city}"
        self.producer.mkdir()
        self.path = self.producer / "hourly.csv"
        zone = timezone(timedelta(hours=8)) if dataset == "urbanev" else None
        self.start = datetime(2023, 6, 1, tzinfo=zone)
        self.deployment = datetime(2023, 7, 1, tzinfo=zone)
        self.stop = datetime(2023, 7, 3, tzinfo=zone)
        entities = ("001", "002", "005")
        rows = []
        pairs = (
            ((entity, hour) for entity in entities for hour in range(768))
            if entity_major
            else ((entity, hour) for hour in range(768) for entity in entities)
        )
        for entity, hour in pairs:
            count = 12 if dataset == "urbanev" else 1
            rows.append(
                [
                    dataset,
                    city,
                    entity,
                    (self.start + timedelta(hours=hour)).isoformat(),
                    "20",
                    "1",
                    str(count),
                    str(count),
                    "",
                ]
            )
        self.write_rows(rows)
        config = {
            "start_inclusive": self.start.isoformat(),
            "end_exclusive": self.stop.isoformat(),
            "clock_policy": "publisher-local-naive",
            "interval_label_assumption": "start",
        }
        output = {
            "path": "hourly.csv",
            "sha256": digest(self.path),
            "size_bytes": self.path.stat().st_size,
        }
        self.manifest = {"run_id": "fixture-producer-v1", "config": config}
        if dataset == "charged":
            self.manifest.update(
                status="technical_success; input acceptance pending peer review",
                contract_profile="charged-hourly-v1-local-naive",
                cities=[{"city": city, "site_count": 3, "output": output}],
                source_archive={"sha256": "a" * 64},
                code_commit="b" * 40,
                original_observation_status="unknown",
                strict_online_ready=False,
            )
        else:
            config = {
                "start_local": self.start.replace(tzinfo=None).isoformat(),
                "end_local_exclusive": self.stop.replace(tzinfo=None).isoformat(),
                "timezone": "Asia/Shanghai",
                "source_interval_label": "start",
                "output_interval": "[timestamp, timestamp + 1 hour)",
            }
            self.manifest.update(
                config=config,
                status="technical_qc_pass",
                summary={"station_count": 3},
                archive={"sha256": "a" * 64},
                code={"commit": "b" * 40},
                assumptions={"arrival": "not established"},
                research_acceptance="pending_peer_review",
                output=output,
            )
        self.manifest_path = self.producer / "manifest.json"
        self.refresh_manifest()
        self.config = {
            "producer_manifest": str(self.manifest_path),
            "producer_manifest_sha256": digest(self.manifest_path),
            "dataset_id": dataset,
            "city_id": city,
            "deployment": self.deployment.isoformat(),
            "replay_stop": self.stop.isoformat(),
            "source_start": self.start.isoformat(),
            "history_days": 7,
            "split_salt": "fixture-only-v1",
            "availability_delay_hours": 0,
        }

    def write_rows(self, rows):
        with self.path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(HEADER)
            writer.writerows(rows)

    def refresh_manifest(self):
        output = (
            self.manifest["output"]
            if self.dataset == "urbanev"
            else self.manifest["cities"][0]["output"]
        )
        output.update(sha256=digest(self.path), size_bytes=self.path.stat().st_size)
        self.manifest_path.write_text(json.dumps(self.manifest))
        if hasattr(self, "config"):
            self.config["producer_manifest_sha256"] = digest(self.manifest_path)

    def change_rows(self, change):
        with self.path.open(newline="") as stream:
            rows = list(csv.reader(stream))[1:]
        self.write_rows(change(rows))
        self.refresh_manifest()

    def run_loader(self, name="run", **updates):
        return run_inputs({**self.config, **updates}, self.root / name)

    def test_complete_charged_integration_and_predictor_reader(self):
        raw_hash = digest(self.path)
        manifest = self.run_loader()
        self.assertEqual(manifest["status"], "technical_success")
        self.assertEqual(
            manifest["counts"],
            {
                "source": 1,
                "development": 1,
                "final": 1,
                "undefined_scales": 0,
                "initial_candidates": 41,
                "initial_trainable": 41,
                "scheduled_forecasts": 4,
            },
        )
        forecasts = list(
            iter_forecasts(
                self.root / "run", expected_manifest_sha256=digest(self.root / "run/manifest.json")
            )
        )
        self.assertEqual(len(forecasts), 4)
        self.assertEqual({record["identity"][2] for record in forecasts}, {"001", "005"})
        self.assertEqual(forecasts[0]["x_hist"][0][0], 1)
        self.assertEqual((len(forecasts[0]["x_hist"]), len(forecasts[0]["x_hist"][0])), (24, 7))
        self.assertEqual(len(forecasts[0]["c_future"][0]), 5)
        self.assertFalse({"y_kwh", "y_scaled", "file_valid", "available_at"} & forecasts[0].keys())
        examples = json_lines(self.root / "run/training.jsonl")
        self.assertEqual(len(examples), 41)
        for example in examples:
            self.assertLessEqual(
                datetime.fromisoformat(example["forecast"]["origin"]) + timedelta(days=1),
                self.deployment,
            )
        for record in json_lines(self.root / "run/entities.jsonl"):
            self.assertEqual(record["scale"]["energy_scale"], 20)
        self.assertEqual(digest(self.path), raw_hash)
        self.assertFalse((self.root / "run/_hourly.sqlite").exists())
        self.assertIn("ev_inputs/scaling.py", manifest["code"]["executed_sources"])

    def test_all_budgets_have_exact_prefix_and_candidate_counts(self):
        for days, count in ((7, 6), (14, 13), (28, 27)):
            result = self.run_loader(f"budget-{days}", history_days=days, entity_ids=["001"])
            self.assertEqual(result["counts"]["initial_trainable"], count)
            summary = json_lines(self.root / f"budget-{days}/entities.jsonl")[0]
            self.assertEqual(
                summary["fit_start"], (self.deployment - timedelta(days=days)).isoformat()
            )

    def test_future_mutation_cannot_change_first_forecast_scaler_or_schedule(self):
        self.run_loader("before")

        def mutate(rows):
            for row in rows:
                if row[2] == "001" and datetime.fromisoformat(row[3]) >= self.deployment:
                    row[4], row[5], row[6] = "", "0", "0"
            return rows

        self.change_rows(mutate)
        self.run_loader("after")
        before = json_lines(self.root / "before/forecasts.jsonl")
        after = json_lines(self.root / "after/forecasts.jsonl")
        self.assertEqual(
            [(x["identity"], x["origin"]) for x in before],
            [(x["identity"], x["origin"]) for x in after],
        )
        before[0].pop("input_run_id")
        after[0].pop("input_run_id")
        self.assertEqual(before[0], after[0])
        self.assertIsNone(json_lines(self.root / "after/labels.jsonl")[0]["energy_kwh"][0])
        a = json_lines(self.root / "before/entities.jsonl")[0]["scale"]
        b = json_lines(self.root / "after/entities.jsonl")[0]["scale"]
        self.assertEqual(a, b)
        summary = json_lines(self.root / "after/entities.jsonl")[0]
        self.assertEqual(summary["all_missing_replay_histories"], 1)

    def test_delay_is_explicit_and_skips_initial_labels_without_filling(self):
        result = self.run_loader(availability_delay_hours=2, entity_ids=["001"])
        self.assertEqual(result["counts"]["initial_candidates"], 6)
        self.assertEqual(result["counts"]["initial_trainable"], 5)
        summary = json_lines(self.root / "run/entities.jsonl")[0]
        self.assertEqual(summary["skipped_delayed_labels"], 1)
        self.assertEqual(summary["scale"]["valid_count"], 166)
        forecast = json_lines(self.root / "run/forecasts.jsonl")[0]
        self.assertEqual(forecast["x_hist"][-1][0], 0)
        self.assertEqual(forecast["x_hist"][-1][-1], 0)

    def test_true_zero_keeps_labels_and_explicit_fallback(self):
        def zeros(rows):
            for row in rows:
                if row[2] == "001":
                    row[4] = "0"
            return rows

        self.change_rows(zeros)
        result = self.run_loader(entity_ids=["001"])
        self.assertEqual(result["counts"]["initial_trainable"], 6)
        summary = json_lines(self.root / "run/entities.jsonl")[0]
        self.assertEqual(summary["scale"]["fallback"], "zero-p95-unit-kwh")
        forecast = json_lines(self.root / "run/forecasts.jsonl")[0]
        self.assertEqual((forecast["x_hist"][0][0], forecast["x_hist"][0][-1]), (0, 1))

    def test_empty_prefix_is_recorded_and_run_is_incomplete(self):
        def missing(rows):
            for row in rows:
                if row[2] == "001":
                    row[4], row[5], row[6] = "", "0", "0"
            return rows

        self.change_rows(missing)
        result = self.run_loader(entity_ids=["001"])
        self.assertEqual(result["status"], "incomplete_undefined_scales")
        self.assertEqual(result["counts"]["final"], 1)
        self.assertEqual(
            json_lines(self.root / "run/entities.jsonl")[0]["status"], "undefined_scale"
        )
        with self.assertRaises(ValueError):
            list(
                iter_forecasts(
                    self.root / "run",
                    expected_manifest_sha256=digest(self.root / "run/manifest.json"),
                )
            )

    def test_manifest_or_hourly_corruption_rejected(self):
        with self.assertRaisesRegex(ValueError, "manifest fingerprint"):
            self.run_loader("bad-manifest", producer_manifest_sha256="0" * 64)
        self.path.write_text(self.path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "size/fingerprint"):
            self.run_loader("bad-file")

    def test_structural_gap_fails_and_leaves_failure_evidence(self):
        self.change_rows(lambda rows: rows[1:])
        with self.assertRaisesRegex(ValueError, "Gap/duplicate"):
            self.run_loader()
        self.assertEqual(
            json.loads((self.root / "run/manifest.json").read_text())["status"], "failed"
        )
        self.assertFalse((self.root / "run/_hourly.sqlite").exists())

    def test_wrong_namespace_and_malformed_valid_energy_fail(self):
        def wrong(rows):
            rows[0][0] = "urbanev"
            return rows

        self.change_rows(wrong)
        with self.assertRaisesRegex(ValueError, "Wrong identity"):
            self.run_loader()

    def test_unknown_profile_failed_status_and_unsafe_member_rejected(self):
        self.manifest["contract_profile"] = "guess-utc"
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "clock profile"):
            self.run_loader("profile")
        self.manifest["contract_profile"] = "charged-hourly-v1-local-naive"
        self.manifest["status"] = "failed"
        self.refresh_manifest()
        with self.assertRaises(ValueError):
            self.run_loader("status")
        self.manifest["status"] = "technical_success; input acceptance pending peer review"
        self.manifest["cities"][0]["output"]["path"] = "../outside.csv"
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.run_loader("path")

    def test_bad_bounds_budget_selection_and_implicit_policy_rejected(self):
        cases = (
            {"deployment": "2023-07-01T00:00:00+00:00"},
            {"history_days": 8},
            {"source_start": "2023-05-01T00:00:00"},
            {"availability_delay_hours": -1},
            {"entity_ids": ["not-present"]},
        )
        for index, updates in enumerate(cases):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                self.run_loader(f"bad-{index}", **updates)
        config = {**self.config}
        config.pop("availability_delay_hours")
        with self.assertRaisesRegex(ValueError, "config fields"):
            run_inputs(config, self.root / "missing-policy")

    def test_existing_output_never_overwritten(self):
        self.run_loader()
        original = digest(self.root / "run/manifest.json")
        with self.assertRaises(FileExistsError):
            self.run_loader()
        self.assertEqual(digest(self.root / "run/manifest.json"), original)
        with self.assertRaisesRegex(ValueError, "separate"):
            run_inputs(self.config, self.root / "data/raw/forbidden-run")

    def test_predictor_reader_does_not_open_labels_and_rejects_extra_y(self):
        self.run_loader(entity_ids=["001"])
        run = self.root / "run"
        (run / "labels.jsonl").unlink()
        self.assertEqual(
            len(list(iter_forecasts(run, expected_manifest_sha256=digest(run / "manifest.json")))),
            2,
        )
        path = run / "forecasts.jsonl"
        records = json_lines(path)
        records[0]["y_kwh"] = [999] * 24
        path.write_text("\n".join(json.dumps(row) for row in records) + "\n")
        manifest = json.loads((run / "manifest.json").read_text())
        manifest["files"][path.name]["sha256"] = digest(path)
        (run / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "unexpected/missing"):
            list(iter_forecasts(run, expected_manifest_sha256=digest(run / "manifest.json")))

    def test_urbanev_entity_major_profile_and_fixed_offset(self):
        self.make_source(dataset="urbanev", city="SZH", entity_major=True)
        result = self.run_loader("urban")
        self.assertEqual(result["status"], "technical_success")
        self.assertEqual(result["source"]["clock_mode"], "offset-aware-local")
        forecasts = json_lines(self.root / "urban/forecasts.jsonl")
        for forecast in forecasts:
            self.assertTrue(forecast["origin"].endswith("+08:00"))
            self.assertEqual(forecast["c_future"][0][:2], [0, 1])

    def test_all_six_charged_city_profiles_remain_separate(self):
        for city in ("AMS", "JHB", "LOA", "MEL", "SPO", "SZH"):
            if city != "AMS":
                self.make_source(city=city)
            source = read_source(
                self.manifest_path,
                expected_manifest_sha256=digest(self.manifest_path),
                dataset_id="charged",
                city_id=city,
            )
            self.assertEqual(source.city_id, city)
            self.assertIsNone(source.start.tzinfo)

    def test_cli_relative_config_and_nonzero_failure(self):
        config = {
            **self.config,
            "producer_manifest": f"{self.producer.name}/manifest.json",
            "entity_ids": ["001"],
        }
        path = self.root / "config.json"
        path.write_text(json.dumps(config))
        command = [
            sys.executable,
            "-m",
            "tools.model_inputs",
            "--config",
            str(path),
            "--output",
            str(self.root / "cli"),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input loader failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
