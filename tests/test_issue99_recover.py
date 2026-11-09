"""Explicit recovery preserves partial trial bytes and ledger chain."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ev_models.checkpoint import digest
from ev_runner.continuous_run import code_identity
from ev_search.fixed import FixedSearchConfig
from ev_search.ledger import FixedLedger
from ev_search.protocol import canonical_sha256
from ev_search.recover import recover_interrupted_trial

ROOT = Path(__file__).resolve().parents[1]


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.search_path = ROOT / "configs/issue99-fixed-search-v1.json"
        self.study_path = ROOT / "configs/issue99-study-calibration-v1.json"
        self.search = FixedSearchConfig(**json.loads(self.search_path.read_text()))
        self.study = json.loads(self.study_path.read_text())
        self.protocol_path = self.root / "protocol.json"
        self.protocol = {
            "status": "locked_owner_approved",
            "owner_authorization": "synthetic test",
            "code_commit": code_identity()["commit"],
            "fixed_search_config_sha256": digest(self.search_path),
            "calibration_study_template_sha256": canonical_sha256(self.study),
            "evaluation_study_template_sha256": "a" * 64,
            "input_manifest_sha256": "b" * 64,
            "source_population_sha256": "c" * 64,
            "source_checkpoint_sha256": {str(seed): "d" * 64 for seed in (42, 43, 44)},
        }
        self.protocol_path.write_text(json.dumps(self.protocol), encoding="utf-8")
        self.binding = {
            "schema": "issue99-fixed-calibration-binding-v1",
            "input_manifest_sha256": self.protocol["input_manifest_sha256"],
            "source_population_sha256": self.protocol["source_population_sha256"],
            "protocol_sha256": digest(self.protocol_path),
            "calibration_study_template_sha256": canonical_sha256(self.study),
            "fixed_search_config_sha256": digest(self.search_path),
            "code_commit": self.protocol["code_commit"],
            "sources": self.protocol["source_checkpoint_sha256"],
            "code_files": {
                str(path.relative_to(ROOT)): digest(path)
                for path in sorted((ROOT / "ev_search").glob("*.py"))
            },
            "runner_code_files": code_identity()["files"],
        }
        self.ledger_root = self.root / "fixed"
        self.ledger = FixedLedger(self.ledger_root, self.search, binding=self.binding)

    def recover(self):
        return recover_interrupted_trial(
            self.ledger_root, self.protocol_path, self.search_path, self.study_path
        )

    def test_explicitly_closes_one_interrupted_trial(self):
        self.ledger.append(
            {"event": "trial_start", "trial": 0, "lambda": 0.0, "role": "zero_baseline"}
        )
        partial = self.ledger_root / "trial-0000" / "target-1405-seed-42"
        partial.mkdir(parents=True)
        record = partial / "tick-0000.txt"
        record.write_bytes(b"retained")
        original_sha = digest(record)
        result = self.recover()
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["outcome"]["objective_mae_kwh"])
        self.assertEqual(result["outcome"]["recovery_evidence"]["files"], 1)
        self.assertEqual(digest(record), original_sha)
        resumed = FixedLedger(self.ledger_root, self.search, binding=self.binding, resume=True)
        self.assertEqual(len(resumed.completed()), 1)
        self.assertEqual(resumed.completed()[0]["sha256"], result["sha256"])

    def test_no_pending_rejected_without_append(self):
        before = digest(self.ledger_root / "events.jsonl")
        with self.assertRaisesRegex(ValueError, "No single trailing"):
            self.recover()
        self.assertEqual(digest(self.ledger_root / "events.jsonl"), before)

    def test_chain_tampering_rejected_without_append(self):
        self.ledger.append(
            {"event": "trial_start", "trial": 0, "lambda": 0.0, "role": "zero_baseline"}
        )
        (self.ledger_root / "trial-0000").mkdir()
        path = self.ledger_root / "events.jsonl"
        tampered = path.read_bytes().replace(b"zero_baseline", b"fake_baseline")
        path.write_bytes(tampered)
        before = hashlib.sha256(tampered).hexdigest()
        with self.assertRaisesRegex(ValueError, "chain differs"):
            self.recover()
        self.assertEqual(digest(path), before)

    def test_protocol_binding_tampering_rejected(self):
        self.ledger.append(
            {"event": "trial_start", "trial": 0, "lambda": 0.0, "role": "zero_baseline"}
        )
        (self.ledger_root / "trial-0000").mkdir()
        self.protocol["source_population_sha256"] = "e" * 64
        self.protocol_path.write_text(json.dumps(self.protocol), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "binding differs"):
            self.recover()
        with self.assertRaisesRegex(ValueError, "Uncommitted trial"):
            FixedLedger(self.ledger_root, self.search, binding=self.binding, resume=True)


if __name__ == "__main__":
    unittest.main()
