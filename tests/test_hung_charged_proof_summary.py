"""Independent pairing and aggregation checks for supplementary proof summaries."""

import copy
import unittest

from tools.hung_charged_proof_summary import METHODS, summarize_city


def fixture() -> dict:
    rows = []
    for budget in (7, 14, 28):
        for entity in ("1", "2", "3"):
            for seed in (42, 43, 44):
                for method in METHODS:
                    rows.append(
                        {
                            "run_id": f"charged-MEL-{entity}-{budget}d-{method}-seed{seed}",
                            "issued": 90,
                            "scored": 90,
                            "scored_origins_sha256": f"origins-{budget}-{entity}-{seed}",
                            "mae_kwh": 2.0 if method == "target_only" else 1.0,
                            "rmse_kwh": 3.0,
                        }
                    )
    return {"status": "verified", "runs": rows}


class ProofSummaryTests(unittest.TestCase):
    def test_equal_station_seed_aggregation(self) -> None:
        proof = fixture()
        for row in proof["runs"]:
            if row["run_id"] == "charged-MEL-1-7d-adaptive-seed42":
                row["mae_kwh"] = 7.0
        summary = summarize_city("MEL", proof)
        self.assertAlmostEqual(summary[0]["mean_mae_gain_kwh"], 1.0 / 3.0)
        self.assertEqual(summary[0]["worse_station_count"], 1)
        self.assertEqual(summary[1]["worse_station_count"], 0)

    def test_rejects_mismatched_origins_and_duplicate_ids(self) -> None:
        proof = fixture()
        bad = copy.deepcopy(proof)
        bad["runs"][0]["scored_origins_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "Unpaired scored origins"):
            summarize_city("MEL", bad)
        bad = copy.deepcopy(proof)
        bad["runs"][0]["run_id"] = bad["runs"][1]["run_id"]
        with self.assertRaisesRegex(ValueError, "duplicate run ID"):
            summarize_city("MEL", bad)


if __name__ == "__main__":
    unittest.main()
