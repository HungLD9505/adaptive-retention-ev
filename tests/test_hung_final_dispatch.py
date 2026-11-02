"""Synthetic lock, Final-role execution and create-only readback checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ev_inputs.hourly_reader import sha256_file
from experiments.supporting_pipeline.final_dispatch import dispatch
from experiments.supporting_pipeline.final_lock import MIN_FREE_BYTES, validate_lock
from tests.test_hung_final_role_replay import final_fixture

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8", newline="\n")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _fixture(root: Path) -> tuple[Path, str, Path, Path]:
    input_run, manifest_sha = final_fixture(root, days=90)
    package = root / "final-input-package.zip"
    package.write_bytes(b"synthetic-package")
    analysis = root / "analysis.json"
    analysis.write_text("{}\n", encoding="utf-8")
    job = {
        "job_id": "seasonal_b7s7e_dev1",
        "variant": "seasonal_naive",
        "entity_id": "dev-1",
        "dataset_id": "urbanev",
        "city_id": "SZH",
        "budget_days": 7,
        "seed": 7,
        "method": "seasonal_naive",
        "input_run": str(input_run),
        "input_manifest_sha256": manifest_sha,
        "source_checkpoint_sha256": None,
        "target_checkpoint_sha256": None,
    }
    jobset = _write_json(
        root / "locks" / "jobset.json", {"schema": "hung-final-jobset-v1", "jobs": [job]}
    )
    jobset["count"] = 1
    plan = _write_json(
        root / "locks" / "execution-plan.json",
        {
            "schema": "hung-final-execution-plan-v1",
            "jobs": [
                {
                    "job_id": job["job_id"],
                    "variant": job["variant"],
                    "method": job["method"],
                    "target_init": None,
                    "replay": {
                        "input_run": str(input_run),
                        "manifest_sha256": manifest_sha,
                        "entity_id": "dev-1",
                        "method": "seasonal_naive",
                        "initial_checkpoint": None,
                        "source_input_run": None,
                        "source_manifest_sha256": None,
                        "source_checkpoint": None,
                        "resume_checkpoint": None,
                        "block_days": 14,
                        "max_origins": 90,
                        "device": "cpu",
                        "seed": 7,
                    },
                }
            ],
        },
    )
    lock = {
        "schema": "hung-final-lock-v1",
        "scope": "final_only",
        "code_commit": "0" * 40,
        "authorization": {
            "issue_url": "https://github.com/HungLD9505/adaptive-retention-ev/issues/23",
            "comment_id": 6476049006,
            "review_state": "lead_exception_not_peer_approval",
        },
        "report1_contract": {
            "head_topology": "declared synthetic topology",
            "bootstrap_rule": "declared synthetic bootstrap",
            "controller_rule": "declared synthetic controller",
            "causal_label_rule": "forecast before label",
        },
        "drift_reference": {
            "schema": "hung-final-drift-reference-v1",
            "rule": "first_created_final_forecast_valid_load_population_sd",
            "scale_floor": 0.1,
        },
        "input": {
            "path": str(package),
            "bytes": package.stat().st_size,
            "sha256": sha256_file(package),
        },
        "source_checkpoints": [],
        "jobset": jobset,
        "execution_plan": plan,
        "analysis": {
            "path": str(analysis),
            "bytes": analysis.stat().st_size,
            "sha256": sha256_file(analysis),
        },
        "coverage": {
            "selected_entities": [
                {"dataset_id": "urbanev", "city_id": "SZH", "entity_id": "dev-1"}
            ],
            "budgets": [7, 14, 28],
            "seeds": [7, 11, 19],
            "variants": ["seasonal_naive"],
            "variant_categories": {"seasonal_naive": ["baseline:seasonal_naive"]},
            "variant_seed_policy": {
                "seasonal_naive": {
                    "deterministic_representative_seed": 7,
                    "alias_seeds": [11, 19],
                }
            },
            "replay_origins": 90,
            "expected_jobs": 3,
            "missing_cells": [
                {
                    "dataset_id": "urbanev",
                    "city_id": "SZH",
                    "entity_id": "dev-1",
                    "budget_days": budget,
                    "seed": 7,
                    "variant": "seasonal_naive",
                    "reason": "Synthetic fixture has only budget seven",
                }
                for budget in (14, 28)
            ],
            "declared_shortfalls": ["Synthetic fixture contains one of three physical cells"],
        },
        "resources": {
            "provider": "local",
            "device": "cpu",
            "min_free_bytes": MIN_FREE_BYTES,
            "estimated_gpu_seconds": 0,
            "estimated_output_bytes": 1_000_000,
        },
        "output_root": str(root / "out"),
        "created_at_utc": "2026-10-29T00:00:00Z",
        "final_label_access_after_lock": True,
    }
    reference = _write_json(root / "locks" / "lock.json", lock)
    return Path(reference["path"]), reference["sha256"], root / "out", Path(jobset["path"])


class FinalDispatchTests(unittest.TestCase):
    def test_all_prior_stages_are_checked_before_any_new_job(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            lock_sha = "b" * 64
            (root / "final_lock_identity.json").write_text(
                json.dumps({"schema": "hung-final-output-identity-v1", "lock_sha256": lock_sha}),
                encoding="utf-8",
            )
            context = {
                "output_root": root,
                "lock_sha256": lock_sha,
                "lock": {
                    "resources": {"min_free_bytes": MIN_FREE_BYTES, "estimated_output_bytes": 1}
                },
                "coverage_status": "incomplete",
                "input_runs_verified": True,
                "jobs": [
                    {"job_id": "a", "method": "seasonal_naive"},
                    {"job_id": "b", "method": "seasonal_naive"},
                ],
                "plan": [{"target_init": None}, {"target_init": None}],
            }

            def prior_stage(_root: Path, job_id: str, stage: str, _sha: str) -> None:
                if job_id == "b" and stage == "replay":
                    raise ValueError("Corrupt later stage")

            with (
                mock.patch(
                    "experiments.supporting_pipeline.final_dispatch._free_bytes",
                    return_value=2 * MIN_FREE_BYTES,
                ),
                mock.patch(
                    "experiments.supporting_pipeline.final_dispatch._verified_stage",
                    side_effect=prior_stage,
                ),
                mock.patch("experiments.supporting_pipeline.final_dispatch._run_job") as execute,
            ):
                with self.assertRaisesRegex(ValueError, "Corrupt later stage"):
                    dispatch(context, run=True)
                execute.assert_not_called()

    def test_synthetic_final_run_reverifies_and_rejects_changed_bytes(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            lock_path, lock_sha, output, _ = _fixture(Path(directory))
            context = validate_lock(lock_path, lock_sha, check_code=False)
            with mock.patch(
                "experiments.supporting_pipeline.final_dispatch._free_bytes",
                return_value=2 * MIN_FREE_BYTES,
            ):
                self.assertEqual(dispatch(context, run=True)["verified"], 1)
                self.assertEqual(dispatch(context, run=True)["verified"], 1)
            self.assertEqual(dispatch(context, run=False)["status"], "jobset_complete")
            self.assertEqual(dispatch(context, run=False)["coverage_status"], "incomplete")
            journal = output / "stages" / "seasonal_b7s7e_dev1" / "replay" / "forecasts.jsonl"
            with journal.open("a", encoding="utf-8") as stream:
                stream.write("tampered\n")
            with self.assertRaisesRegex(ValueError, "Receipt identity/output mismatch"):
                dispatch(context, run=False)

    def test_lock_mutation_and_capacity_fail_closed_before_output(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            lock_path, lock_sha, output, jobset = _fixture(Path(directory))
            context = validate_lock(lock_path, lock_sha, check_code=False)
            with mock.patch(
                "experiments.supporting_pipeline.final_dispatch._free_bytes", return_value=1
            ):
                with self.assertRaisesRegex(ValueError, "reserve plus locked output budget"):
                    dispatch(context, run=True)
            self.assertFalse(output.exists())
            budget = context["lock"]["resources"]
            with mock.patch(
                "experiments.supporting_pipeline.final_dispatch._free_bytes",
                return_value=budget["min_free_bytes"] + budget["estimated_output_bytes"] - 1,
            ):
                with self.assertRaisesRegex(ValueError, "reserve plus locked output budget"):
                    dispatch(context, run=True)
            self.assertFalse(output.exists())
            with jobset.open("a", encoding="utf-8") as stream:
                stream.write(" ")
            with self.assertRaisesRegex(ValueError, "Pinned file bytes differ"):
                validate_lock(lock_path, lock_sha, check_code=False)

    def test_precheckout_capacity_witness_does_not_repeat_full_budget(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            lock_path, lock_sha, output, _ = _fixture(Path(directory))
            context = validate_lock(lock_path, lock_sha, check_code=False)
            with mock.patch(
                "experiments.supporting_pipeline.final_dispatch._free_bytes",
                return_value=MIN_FREE_BYTES + 1,
            ):
                with self.assertRaisesRegex(ValueError, "reserve plus locked output budget"):
                    dispatch(
                        context, run=True, provider_initial_free_bytes=MIN_FREE_BYTES + 999_999
                    )
                self.assertFalse(output.exists())
                self.assertEqual(
                    dispatch(
                        context,
                        run=True,
                        provider_initial_free_bytes=MIN_FREE_BYTES + 1_000_000,
                    )["verified"],
                    1,
                )
                self.assertEqual(dispatch(context, run=True)["verified"], 1)
