"""Independent metadata fixtures; these are not GPU compatibility evidence."""

import copy
import json
import unittest

from tools.hardware_execution_lock import ARRAYS, CHECKS, SCIENTIFIC_COMMIT, build_child, sha256


def encode(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True).encode()


class HardwareChildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = {
            "schema": "ev-final-execution-lock-v1",
            "whole_units": 810,
            "method_seed_cells": 11340,
            "files": {f"fixture/{i}.py": str(i) for i in range(139)},
            "unit_order": [{"index": i} for i in range(810)],
            "runtime_packages_path": "packages.json",
            "runtime_profile": {
                "python": "fixture-python",
                "torch": "fixture-torch",
                "cuda": "fixture-cuda",
                "device": "cuda",
                "device_name": "Tesla T4",
                "deterministic_algorithms": True,
            },
            "groups": [{"sources": {"42": {"sha256": "frozen-source"}}}],
            "method_configs": {"42": {"adaptive": {"unchanged": True}}},
            "independent_peer_approval": False,
        }
        self.parent["files"]["packages.json"] = "fixture-packages-pin"
        self.parent_raw = encode(self.parent)
        self.parent_sha = sha256(self.parent_raw)
        self.profile = self.parent["runtime_profile"] | {"device_name": "NVIDIA L4"}
        self.auth = {
            "schema": "ev-final-hardware-authorization-v1",
            "parent_lock_sha256": self.parent_sha,
            "hardware_extension_authorized": True,
            "independent_peer_approval": False,
            "human_instruction": "Independent test fixture only",
            "evidence_reference": "fixture:authorization",
        }
        self.policy = {
            "schema": "ev-final-hardware-numeric-policy-v1",
            "dtype": "float32",
            "final_outcomes_used": False,
            "bitwise_equality_claimed": False,
            "atol": 0.00001,
            "rtol": 0.0001,
            "declared_epoch": 100,
            "required_arrays": list(ARRAYS),
        }
        self.evidence = {
            "schema": "ev-final-hardware-compatibility-v1",
            "parent_lock_sha256": self.parent_sha,
            "scientific_commit": SCIENTIFIC_COMMIT,
            "scientific_files": copy.deepcopy(self.parent["files"]),
            "runtime_profile": self.profile,
            "runtime_packages_sha256": "fixture-packages-pin",
            "numeric_policy_sha256": sha256(encode(self.policy)),
            "authorization_sha256": sha256(encode(self.auth)),
            "synthetic_only": True,
            "final_values_read": False,
            "source_refits": 0,
            "checks": dict.fromkeys(CHECKS, "PASS"),
            "started_epoch": 200,
            "numeric_comparisons": {
                name: {
                    "shapes_equal": True,
                    "finite_masks_equal": True,
                    "finite_elements": 24,
                    "max_tolerance_ratio": 0.5,
                }
                for name in ARRAYS
            },
            "artifacts": [{"sha256": "a" * 64, "bytes": 123, "reference": "fixture:raw"}],
        }

    def build(self, indices: list[int] | None = None) -> dict:
        return build_child(
            self.parent_raw,
            encode(self.profile),
            encode(self.auth),
            encode(self.policy),
            encode(self.evidence),
            [693, 694] if indices is None else indices,
            expected_parent_sha256=self.parent_sha,
        )

    def test_preserves_all_nonhardware_fields_and_inputs(self) -> None:
        child = self.build()
        for key, value in self.parent.items():
            if key != "runtime_profile":
                self.assertEqual(child[key], value)
        self.assertEqual(child["runtime_profile"]["device_name"], "NVIDIA L4")
        self.assertEqual(self.parent["runtime_profile"]["device_name"], "Tesla T4")
        self.assertFalse(child["hardware_extension"]["dispatch_authorized_by_this_tool"])

    def test_production_default_rejects_fixture_parent(self) -> None:
        with self.assertRaisesRegex(ValueError, "Parent byte identity"):
            build_child(self.parent_raw, b"{}", b"{}", b"{}", b"{}", [693])

    def test_rejects_unsafe_or_reordered_unit_indices(self) -> None:
        for indices in ([], [True], [-1], [810], [694, 693], [693, 693]):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                self.build(indices)

    def test_rejects_software_or_unknown_device_changes(self) -> None:
        for key, value in (("torch", "new"), ("device_name", "unknown"), ("device", "cpu")):
            original = self.profile[key]
            self.profile[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.build()
            self.profile[key] = original

    def test_requires_each_compatibility_check(self) -> None:
        for check in CHECKS:
            self.evidence["checks"][check] = "FAIL"
            with self.subTest(check=check), self.assertRaises(ValueError):
                self.build()
            self.evidence["checks"][check] = "PASS"

    def test_rejects_changed_science_packages_and_real_data(self) -> None:
        for key, value in (
            ("scientific_files", {}),
            ("runtime_packages_sha256", "new"),
            ("scientific_commit", "new"),
            ("final_values_read", True),
            ("source_refits", True),
            ("artifacts", []),
        ):
            original = self.evidence[key]
            self.evidence[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.build()
            self.evidence[key] = original

    def test_policy_must_precede_trial_with_finite_tolerances(self) -> None:
        for key, value in (("declared_epoch", 201), ("atol", True), ("rtol", float("nan"))):
            original = self.policy[key]
            self.policy[key] = value
            self.evidence["numeric_policy_sha256"] = sha256(encode(self.policy))
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.build()
            self.policy[key] = original

    def test_no_invented_peer_approval(self) -> None:
        self.auth["independent_peer_approval"] = True
        with self.assertRaises(ValueError):
            self.build()

    def test_numeric_failure_is_not_hidden_by_pass_string(self) -> None:
        for value in (1.01, float("inf"), True, -1):
            self.evidence["numeric_comparisons"]["predictions"]["max_tolerance_ratio"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.build()


if __name__ == "__main__":
    unittest.main()
