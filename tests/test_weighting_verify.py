"""Verifier guards must reject tampering even when Python assertions are disabled."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ev_models.checkpoint import digest

ROOT = Path(__file__).resolve().parents[1]
METHODS = ["no_share", "decreasing_share", "adahedge", "ftl"]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def fixture(root: Path) -> tuple[Path, Path]:
    """Independent zero-error one-day matrix: all methods tie, first candidate wins."""
    vectors = [[1.0] * 24]
    cell = dict(
        origins=["2026-01-01T00:00:00"],
        available_at=["2026-01-02T00:00:00"],
        stable=vectors,
        fast=vectors,
        labels=vectors,
        scale=1.0,
    )
    original, rows = [], []
    ids = [str(i) for i in range(12)]
    for target in ids:
        for seed in [42, 43, 44]:
            old_arms = {
                name: {"predictions_kwh": vectors}
                for name in ["stable_fixed", "fast_only", "static_mix", "fixed_share"]
            }
            original.append(dict(target=target, seed=seed, cell=copy.deepcopy(cell), arms=old_arms))
            arms = {
                name: {"predictions_kwh": vectors} for name in ["fixed", "fast", "static", "legacy"]
            }
            for name in METHODS:
                arms[name] = dict(
                    weights=[0.5 if name in ["adahedge", "ftl"] else 0.43],
                    predictions_kwh=vectors,
                    daily_mae=[0.0],
                    mae=0.0,
                )
            rows.append(dict(target=target, seed=seed, cell=copy.deepcopy(cell), arms=arms))
    source, prior, protocol_path = root / "source.json", root / "prior.json", root / "protocol.json"
    write_json(source, original)
    write_json(prior, {"status": "synthetic-source-receipt"})
    protocol = dict(
        development_cells=dict(
            path=str(source),
            sha256=digest(source),
            prior_verification_path=str(prior),
            prior_verification_sha256=digest(prior),
        ),
        candidates=METHODS,
        development_ids=ids,
        initial_weight=0.43,
    )
    write_json(protocol_path, protocol)
    output = root / "output"
    output.mkdir()
    write_json(output / "cells.json", rows)
    write_json(
        output / "results.json",
        dict(
            protocol_sha256=digest(protocol_path),
            means={name: 0.0 for name in METHODS + ["fixed", "static", "legacy"]},
            selected="no_share",
            proceed_to_new_cohort=False,
        ),
    )
    return protocol_path, output


class WeightingVerifyTests(unittest.TestCase):
    def invoke(
        self, root: Path, protocol: Path, output: Path, optimized: bool
    ) -> tuple[subprocess.CompletedProcess, Path]:
        receipt = root / ("receipt-optimized.json" if optimized else "receipt-normal.json")
        result = subprocess.run(
            [
                sys.executable,
                *(["-O"] if optimized else []),
                "-m",
                "tools.weighting_verify",
                "--protocol",
                str(protocol),
                "--output",
                str(output),
                "--receipt",
                str(receipt),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return result, receipt

    def test_valid_zero_error_receipt_in_normal_and_optimized_python(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, output = fixture(root)
            for optimized in [False, True]:
                with self.subTest(optimized=optimized):
                    result, receipt = self.invoke(root, protocol, output, optimized)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    saved = json.loads(receipt.read_text())
                    self.assertEqual(saved["status"], "passed")
                    self.assertTrue(saved["stop_rule_reproduced"])

    def test_corrupted_results_fail_without_receipt_under_optimization(self):
        cases = {
            "selected": (lambda value: value.update(selected="ftl"), "Selected method mismatch"),
            "proceed": (
                lambda value: value.update(proceed_to_new_cohort=True),
                "Proceed gate mismatch",
            ),
            "means": (
                lambda value: value["means"].update(no_share=1.0),
                "Candidate aggregate mismatch",
            ),
            "protocol": (
                lambda value: value.update(protocol_sha256="0" * 64),
                "Protocol fingerprint mismatch",
            ),
        }
        for name, (corrupt, message) in cases.items():
            with self.subTest(corruption=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                protocol, output = fixture(root)
                path = output / "results.json"
                value = json.loads(path.read_text())
                corrupt(value)
                write_json(path, value)
                for optimized in [False, True]:
                    with self.subTest(optimized=optimized):
                        result, receipt = self.invoke(root, protocol, output, optimized)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(message, result.stderr)
                        self.assertFalse(receipt.exists())

    def test_source_and_prior_fingerprints_fail_in_optimized_python(self):
        for name, message in [
            ("source.json", "Development source fingerprint mismatch"),
            ("prior.json", "Prior verification fingerprint mismatch"),
        ]:
            with self.subTest(file=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                protocol, output = fixture(root)
                path = root / name
                path.write_text(path.read_text() + " ")
                result, receipt = self.invoke(root, protocol, output, True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertFalse(receipt.exists())

    def test_corrupted_cells_and_mae_fail_in_optimized_python(self):
        for name, message in [
            ("identity", "Source-cell identity mismatch"),
            ("mae", "Candidate MAE mismatch"),
            ("matrix", "Source-cell matrix mismatch"),
        ]:
            with self.subTest(corruption=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                protocol, output = fixture(root)
                path = output / "cells.json"
                rows = json.loads(path.read_text())
                if name == "identity":
                    rows[0]["cell"]["scale"] = 2.0
                elif name == "mae":
                    rows[0]["arms"]["no_share"]["mae"] = 1.0
                else:
                    rows.pop()
                write_json(path, rows)
                result, receipt = self.invoke(root, protocol, output, True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertFalse(receipt.exists())
