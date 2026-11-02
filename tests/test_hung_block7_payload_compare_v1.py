"""Guard the historical Block7 payload comparison against semantic mismatches."""

from __future__ import annotations

import copy
import unittest

import torch

from tools.hung_block7_payload_compare_v1 import (
    REQUIRED_SOURCE,
    REQUIRED_TARGET,
    compare_payload,
)


def checkpoint(role: str, source_sha: str) -> dict:
    value = {key: None for key in (REQUIRED_SOURCE if role == "source" else REQUIRED_TARGET)}
    value.update(
        code_sha="code-old",
        model_state={"weight": torch.tensor([1.0, 2.0])},
        optimizer_state={"step": 3},
        input_binding={"data_sha256": "same"},
    )
    if role == "target":
        value["input_binding"]["source_checkpoint_sha256"] = source_sha
    return value


class PayloadCompareTests(unittest.TestCase):
    def test_source_state_equal_with_code_provenance_difference(self) -> None:
        old = checkpoint("source", "old-source")
        main = copy.deepcopy(old)
        main["code_sha"] = "code-main"
        result = compare_payload(old, main, "source", "old-source", "main-source")
        self.assertEqual(result["different_top_level_fields"], ["code_sha"])

    def test_target_state_equal_with_pinned_source_lineage_difference(self) -> None:
        old = checkpoint("target", "old-source")
        main = copy.deepcopy(old)
        main["code_sha"] = "code-main"
        main["input_binding"]["source_checkpoint_sha256"] = "main-source"
        result = compare_payload(old, main, "target", "old-source", "main-source")
        self.assertEqual(result["different_input_binding_fields"], ["source_checkpoint_sha256"])

    def test_reject_changed_state(self) -> None:
        for changed_field in ("model_state", "optimizer_state"):
            with self.subTest(field=changed_field):
                old = checkpoint("source", "old-source")
                main = copy.deepcopy(old)
                main["code_sha"] = "code-main"
                main[changed_field] = {"different": True}
                with self.assertRaisesRegex(ValueError, "outside permitted provenance metadata"):
                    compare_payload(old, main, "source", "old-source", "main-source")

    def test_reject_wrong_target_source_binding(self) -> None:
        old = checkpoint("target", "old-source")
        main = copy.deepcopy(old)
        main["code_sha"] = "code-main"
        main["input_binding"]["source_checkpoint_sha256"] = "wrong-source"
        with self.assertRaisesRegex(ValueError, "does not match pinned Source"):
            compare_payload(old, main, "target", "old-source", "main-source")
