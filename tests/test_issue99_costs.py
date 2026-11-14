"""Cost reports preserve unknowns and exclude semantically reused model jobs."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.issue99_costs import summarize


class CostTests(unittest.TestCase):
    def test_unknown_historical_and_failed_costs_are_not_replaced_with_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for job, report in [
                ("fixed-1405-seed42", {"invocation_wall_seconds": 2.5}),
                ("discrete-1405-seed42", {"elapsed_seconds": 4.0}),
            ]:
                p = root / "comparison" / job / "run"
                p.mkdir(parents=True)
                (p / "run.json").write_text(json.dumps(report))
            incomplete = root / "fixed" / "trial-0004" / "partial"
            incomplete.mkdir(parents=True)
            (incomplete / "binding.json").write_text("{}")
            jobs = [
                {"job_id": "fixed-1405-seed42", "method": "fixed", "reuse_job_id": None},
                {"job_id": "discrete-1405-seed42", "method": "discrete", "reuse_job_id": None},
                {
                    "job_id": "frozen_lambda-1405-seed42",
                    "method": "frozen_lambda",
                    "reuse_job_id": "fixed-1405-seed42",
                },
            ]
            result = summarize(root, jobs)
            self.assertEqual(result["phases"]["comparison"]["known_wall_seconds"], 6.5)
            self.assertEqual(result["comparison_by_method"]["frozen_lambda"]["invocations"], 0)
            self.assertEqual(result["comparison_by_method"]["frozen_lambda"]["exact_reuse_rows"], 1)
            self.assertIsNone(result["source_pretraining_wall_seconds"])
            self.assertEqual(result["incomplete_invocations_without_report"], 1)
