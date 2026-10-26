"""Independent saved-forecast metrics, pairing and missing-data checks."""

import hashlib
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from tools import hung_results as results


class ResultTests(unittest.TestCase):
    def test_scoring_without_numpy(self):
        state, manifest = self.saved()
        with patch.object(
            torch.Tensor, "numpy", side_effect=RuntimeError("Numpy is not available")
        ):
            row = results.score_saved(state, manifest)
        self.assertEqual(row["metrics"]["mae_kwh"], 2)

    def test_family_keeps_ablation_and_single_baseline_identity(self):
        for family, config in [
            ("parameter_retention", "parameter_retention"),
            ("seasonal_naive", "main"),
            ("drift", "drift_b14s7e1153"),
        ]:
            job = {"id": family + "_b14s7e1153", "cell": "b14s7e1153", "config": config}
            self.assertEqual(results.method_family(job), family)

    def saved(self, errors=(1.0, 3.0)):
        state = {
            "schema": "hung-single-baseline-runner-v1",
            "energy_scale": 2.0,
            "issued": [
                {
                    "day_id": str(i),
                    "prediction": torch.full((1, 24), e / 2),
                    "y_scaled": torch.zeros(24),
                    "normalized_mae": e / 2,
                }
                for i, e in enumerate(errors)
            ],
        }
        manifest = {
            "status": "completed",
            "coverage": {"created": len(errors), "scored": len(errors)},
            "metrics_kwh": {
                "hours": 24 * len(errors),
                "mae_kwh": sum(errors) / len(errors),
                "rmse_kwh": math.sqrt(sum(e * e for e in errors) / len(errors)),
            },
        }
        return state, manifest

    def test_hourly_rmse_not_average_daily_rmse(self):
        state, manifest = self.saved()
        result = results.score_saved(state, manifest)
        self.assertAlmostEqual(result["metrics"]["rmse_kwh"], math.sqrt(5))
        self.assertEqual(result["metrics"]["mae_kwh"], 2)

    def test_forged_metric_fails(self):
        state, manifest = self.saved()
        manifest["metrics_kwh"]["rmse_kwh"] = 2
        with self.assertRaises(ValueError):
            results.score_saved(state, manifest)

    def test_zero_scored_preserves_missing_labels(self):
        state, manifest = self.saved((1.0,))
        state["issued"][0].update(y_scaled=None, normalized_mae=None)
        manifest.update(metrics_kwh=None, coverage={"created": 1, "scored": 0})
        self.assertIsNone(results.score_saved(state, manifest)["metrics"])
        state["issued"][0]["normalized_mae"] = 0.0
        with self.assertRaises(ValueError):
            results.score_saved(state, manifest)

    def test_duplicate_issued_day_fails(self):
        state, manifest = self.saved()
        state["issued"][1]["day_id"] = "0"
        with self.assertRaises(ValueError):
            results.score_saved(state, manifest)

    def test_pair_intersection_and_mismatches(self):
        base = {
            "budget": 14,
            "seed": 7,
            "entity_id": "station",
            "input_manifest_sha256": "input",
            "source_sha256": "source",
            "target_sha256": "target",
        }

        def day(x, label="label"):
            return {"absolute": 24 * x, "squared": 24 * x * x, "label_sha256": label}

        main = {**base, "method": "main", "days": {"a": day(2), "b": day(9)}}
        other = {**base, "method": "ablation", "days": {"a": day(1), "c": day(30)}}
        pairs, blocked = results.paired_results([main, other])
        self.assertFalse(blocked)
        self.assertEqual(pairs[0]["paired_days"], 1)
        self.assertEqual(pairs[0]["method_metrics"]["mae_kwh"], 1)
        for key, value in [("source_sha256", "unmatched"), ("input_manifest_sha256", "wrong")]:
            pairs, blocked = results.paired_results([main, {**other, key: value}])
            self.assertFalse(pairs)
            self.assertEqual(len(blocked), 1)
        other["days"]["a"] = day(1, "different-label")
        self.assertEqual(results.paired_results([main, other])[1][0]["reason"], "label_mismatch")

    def test_equal_station_weight_despite_unequal_seed_coverage(self):
        pairs = []
        for station, seeds, error in [("A", 3, 1), ("B", 1, 9)]:
            for seed in range(seeds):
                pairs.append(
                    {
                        "budget": 14,
                        "method": "main",
                        "reference": "target_only",
                        "uses_source": True,
                        "entity_id": station,
                        "seed": seed,
                        "method_metrics": {"mae_kwh": error, "rmse_kwh": error},
                        "reference_metrics": {"mae_kwh": 4, "rmse_kwh": 4},
                    }
                )
        row = results.station_first(pairs)[0]
        self.assertEqual(row["method_metrics"]["mae_kwh"], 5)
        self.assertEqual(row["minimum_seeds_per_station"], 1)
        self.assertEqual(row["negative_transfer_station_fraction"], 0.5)
        self.assertEqual(row["relative_mae_gain"], -0.25)
        for reference, uses_source in [("main", True), ("target_only", False)]:
            changed = [{**p, "reference": reference, "uses_source": uses_source} for p in pairs]
            generic = results.station_first(changed)[0]
            self.assertIsNone(generic["negative_transfer_station_fraction"])
            self.assertIsNone(generic["transfer_gain"])
            self.assertEqual(generic["worse_than_reference_station_fraction"], 0.5)

    def test_unmatched_catalog_and_changed_bytes_fail(self):
        with self.assertRaises(ValueError):
            results.verify_artifacts(
                {"scope": "development_only", "runs": [{"status": "EXTERNAL_COMPLETE_UNMATCHED"}]},
                Path.cwd(),
            )
        with tempfile.TemporaryDirectory(dir=".") as folder:
            p = Path(folder) / "artifact.json"
            p.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                results.verified_file(
                    {"path": str(p.resolve()), "sha256": hashlib.sha256(b"original").hexdigest()},
                    Path(folder),
                )


if __name__ == "__main__":
    unittest.main()
