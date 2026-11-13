"""Conservative exposure classification without label/forecast access."""

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.confirmation_inventory import inventory, normalize_namespace


class ConfirmationInventoryTests(unittest.TestCase):
    def test_namespace_requires_explicit_dataset_city_and_preserves_case(self):
        self.assertEqual(normalize_namespace(["charged", "AMS"]), "charged-AMS")
        self.assertEqual(normalize_namespace("UrbanEV/SZH"), "urbanev-SZH")
        self.assertIsNone(normalize_namespace("AMS"))

    def test_metadata_only_unknown_is_not_certified_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "docs/reports/issue99-fixture"
            evidence.mkdir(parents=True)
            (evidence / "cells.csv").write_text("namespace,target,mae_kwh\nurbanev-SZH,002,1\n")
            folder = root / "inputs/urbanev-SZH-14d"
            folder.mkdir(parents=True)
            entities = [
                {
                    "identity": ["urbanev", "SZH", target],
                    "role": role,
                    "status": "ready",
                    "initial_trainable": count,
                }
                for target, role, count in [
                    ("001", "source", 13),
                    ("002", "final", 13),
                    ("003", "development", 1),
                    ("004", "final", 0),
                ]
            ]
            entity_path = folder / "entities.jsonl"
            entity_path.write_text("\n".join(map(json.dumps, entities)) + "\n")
            manifest_path = folder / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "config": {"history_days": 14},
                        "files": {
                            "entities.jsonl": {
                                "sha256": hashlib.sha256(entity_path.read_bytes()).hexdigest()
                            }
                        },
                    }
                )
            )
            # No labels, forecasts or training files exist: inventory must not need them.
            result = inventory(root / "inputs", root, root / "output")
            self.assertEqual(result["certified_untouched"], 0)
            self.assertEqual(result["metadata_eligible_exposure_unresolved"], 1)
            with (root / "output/entity-exposure.csv").open() as stream:
                rows = {r["entity_id"]: r for r in csv.DictReader(stream)}
            self.assertEqual(rows["002"]["status"], "excluded_prior_target_or_support")
            self.assertEqual(rows["003"]["status"], "exposure_unresolved")
            self.assertEqual(rows["004"]["status"], "excluded_not_ready_or_no_prefix_examples")
            pinned_path = root / "prior-inventory.json"
            pinned_path.write_text(json.dumps(result))
            pinned = inventory(root / "inputs", root, root / "pinned", prior_manifest=pinned_path)
            self.assertEqual(pinned["namespaces"], result["namespaces"])
            evidence_path = evidence / "cells.csv"
            previous = evidence_path.read_text()
            evidence_path.write_text(previous + " ")
            with self.assertRaisesRegex(ValueError, "Prior evidence fingerprint"):
                inventory(
                    root / "inputs", root, root / "changed-evidence", prior_manifest=pinned_path
                )
            evidence_path.write_text(previous)
            entity_path.write_text(entity_path.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                inventory(root / "inputs", root, root / "tampered")


if __name__ == "__main__":
    unittest.main()
