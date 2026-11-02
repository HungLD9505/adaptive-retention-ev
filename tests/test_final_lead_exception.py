"""Scope-bound lead exception is explicit; integrity and default peer path remain."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ev_models.checkpoint import digest, write_json
from ev_runner.final_gate import authorize, explicit_exception


class LeadExceptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        write_json(self.root / "cohort.json", {"scope": "independent synthetic scope fixture"})
        section = "Explicit one-time override for bounded Final execution."
        self.record = {
            "schema": "ev-explicit-lead-final-exception-v1",
            "independent_peer_approval": False,
            "originating_coordination_chat": "01a13446-0da0-7fd1-b984-e655242b5497",
            "method_seed_cells": 11340,
            "whole_units": 810,
            "entity_budget_pairs": 270,
            "namespace_entity_ids": 90,
            "seeds": [42, 43, 44],
            "history_days": [7, 14, 28],
            "replay_days": 90,
            "cohort_path": "cohort.json",
            "cohort_sha256": digest(self.root / "cohort.json"),
            "issue_section": section,
            "issue_section_sha256": hashlib.sha256(section.encode()).hexdigest(),
            "issue_url": "https://github.com/HungLD9505/adaptive-retention-ev/issues/23",
        }
        write_json(self.root / "exception.json", self.record)
        self.lock = {
            "schema": "ev-final-execution-lock-v1",
            "method_seed_cells": 11340,
            "cohort_path": "cohort.json",
            "runtime_profile": {"device": "cuda"},
            "files": {name: digest(self.root / name) for name in ("exception.json", "cohort.json")},
            "authorization_policy": {
                "mode": "explicit_lead_exception",
                "record_path": "exception.json",
            },
        }
        write_json(self.root / "lock.json", self.lock)

    def test_explicit_exception_is_offline_and_never_claims_peer_review(self):
        def git(args, **kwargs):
            self.assertEqual(args[0], "git", "Exception path must not need remote credentials")
            if "rev-parse" in args:
                return "fixture-head\n"
            if "status" in args:
                return ""
            return (self.root / args[-1].removeprefix("HEAD:")).read_bytes()

        with patch("ev_runner.final_gate.subprocess.check_output", side_effect=git):
            access = authorize(self.root / "lock.json", self.root)
        provenance = access.provenance()
        self.assertFalse(provenance["independent_peer_approval"])
        self.assertEqual(len(provenance["execution_code_identity_sha256"]), 64)
        self.assertNotIn("reviewed_commit", provenance)
        self.assertNotIn("review", provenance)
        (self.root / "cohort.json").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "dependency changed"):
            access.check()

    def test_scope_or_record_mutation_and_unknown_policy_fail(self):
        self.assertIsNotNone(explicit_exception(self.root, self.lock))
        for field, value in (
            ("method_seed_cells", 42),
            ("seeds", [42]),
            ("independent_peer_approval", True),
        ):
            changed = {**self.record, field: value}
            (self.root / "exception.json").write_text(json.dumps(changed))
            self.lock["files"]["exception.json"] = digest(self.root / "exception.json")
            with self.subTest(field=field), self.assertRaises(ValueError):
                explicit_exception(self.root, self.lock)
        self.lock["authorization_policy"]["mode"] = "skip-integrity"
        with self.assertRaises(ValueError):
            explicit_exception(self.root, self.lock)

    def test_default_still_requires_peer_review_and_missing_receipt_fails(self):
        self.assertIsNone(explicit_exception(self.root, {"files": {}}))
        self.lock["files"]["exception.json"] = "0" * 64
        with self.assertRaises(ValueError):
            explicit_exception(self.root, self.lock)
