"""Small invariant checks for the Development-only audit."""

import unittest

from tools.hung_development_audit import exact_station_bootstrap, zero_score_audit


class DevelopmentAuditTests(unittest.TestCase):
    def test_station_bootstrap_is_exact_and_deterministic(self) -> None:
        self.assertEqual(exact_station_bootstrap([2.0, 2.0, 2.0]), (2.0, 2.0))
        low, high = exact_station_bootstrap([1.0, 3.0])
        self.assertEqual((low, high), (1.075, 2.925))

    def test_zero_score_rejects_unscored_forecast_mismatch(self) -> None:
        row = {
            "job_id": "sample",
            "budget": 7,
            "entity_id": "1",
            "metrics": None,
            "coverage": {"requested": 90, "created": 59, "scored": 0, "unscored_created": 58},
        }
        with self.assertRaisesRegex(ValueError, "Unexpected zero-score coverage"):
            zero_score_audit({"runs": [row]})


if __name__ == "__main__":
    unittest.main()
