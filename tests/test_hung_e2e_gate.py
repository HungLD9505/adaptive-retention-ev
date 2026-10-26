"""Independent checks of exact state comparison used for fairness diagnostics."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from experiments.hung_sprint2 import dispatch_matched as dispatch
from tools.hung_e2e_gate import charged_evidence, equal_state


class StateComparisonTests(unittest.TestCase):
    def test_collection_evidence_rehash_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory(dir=dispatch.ROOT / ".cache") as folder:
            path = Path(folder) / "proof.json"
            path.write_text("{}", encoding="utf-8")
            pin = {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": dispatch.sha256_file(path),
            }
            handoff = {
                "schema": "charged-six-city-development-handoff-v1",
                "run_count": 1,
                "cities": {
                    "JHB": {"files": {"daily": pin}, "runs": 1, "source_code_commit": "fixture"}
                },
            }
            with patch("tools.hung_e2e_gate.pinned_json", return_value=handoff):
                result = charged_evidence({})
                self.assertEqual(result["evidence_files_rehashed"], 1)
                self.assertIn("not freshly restored", result["cities"]["JHB"]["scope"])
                path.write_text(json.dumps({"changed": True}), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    charged_evidence({})

    def test_compares_values_dtype_shape_and_rng_without_tolerance(self):
        a = {"weights": torch.tensor([1.0, 2.0]), "optimizer": {0: [torch.tensor(3)]}, "seed": 7}
        b = {"weights": torch.tensor([1.0, 2.0]), "optimizer": {0: [torch.tensor(3)]}, "seed": 7}
        self.assertTrue(equal_state(a, b))
        b["weights"][0] += 0.001
        self.assertFalse(equal_state(a, b))
        self.assertFalse(equal_state(torch.ones(2), torch.ones(2, dtype=torch.float64)))
        self.assertFalse(equal_state(torch.ones(2), torch.ones(1, 2)))
        self.assertFalse(equal_state([1, 2], (1, 2)))
        self.assertFalse(equal_state({"seed": 7}, {"seed": 11}))


if __name__ == "__main__":
    unittest.main()
