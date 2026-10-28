"""Outcome-blind Final lock gate tests; no provider or Final role access."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from experiments.hung_sprint2.final_lock import MIN_FREE_BYTES, validate_lock
from tools.hung_final_lock_preflight import _attestation, _candidate, _pin, prepare_lock

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/reports/hung-final-candidate-jobset-20261029-v1"
ANALYSIS = (
    ROOT / "docs/reports/hung-final-execution-contract-candidate-20261029-v1/analysis_spec.json"
)
SOURCES = (
    ROOT
    / "docs/reports/hung-final-metadata-preflight-20261029-v1/development_source_candidates.csv"
)
RESOURCE = ROOT / "docs/reports/hung-final-resource-preflight-20261029-v2/candidate_scenarios.csv"
INPUT_ZIP = ROOT / ".cache/kaggle-payload-v2/payload/inputs.zip"
NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class FinalLockPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.evidence = self.base / "provider-response.json"
        self.attestation = self.base / "attestation.json"
        self.analysis = self.base / "analysis.json"
        self.packet = self.base / "lock-packet"
        self.output = self.base / "output"
        self.spec = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        for group, prefix in (
            ("executed_hung_code_sha256", "experiments/hung_sprint2"),
            ("development_analysis_code_sha256", ""),
            ("prepared_final_durability_code_sha256", ""),
        ):
            for name in self.spec[group]:
                self.spec[group][name] = _pin(ROOT / prefix / name)["sha256"]
        write_json(self.analysis, self.spec)
        self.write_attestation()

    def write_attestation(
        self,
        *,
        observed: datetime = NOW,
        gpu_seconds: int = 25_000,
        provider_bytes: int = 30_000_000_000,
    ) -> None:
        raw = {
            "provider": "kaggle",
            "account": "hungluongduc",
            "observed_at_utc": observed.isoformat(),
            "gpu_seconds_available": gpu_seconds,
            "provider_storage_free_bytes": provider_bytes,
            "is_pay_to_scale_enabled": False,
        }
        write_json(self.evidence, raw)
        write_json(
            self.attestation,
            {
                "schema": "hung-final-provider-attestation-v1",
                "provider": "kaggle",
                "account": "hungluongduc",
                "observed_at_utc": observed.isoformat(),
                "authentication_method": "authenticated_kaggle_api",
                "evidence": _pin(self.evidence),
                "gpu_seconds_available": gpu_seconds,
                "provider_storage_free_bytes": provider_bytes,
                "is_pay_to_scale_enabled": False,
            },
        )

    def args(self) -> dict:
        return {
            "root": ROOT,
            "candidate_dir": CANDIDATE,
            "analysis_path": self.analysis,
            "source_csv": SOURCES,
            "resource_csv": RESOURCE,
            "input_zip": INPUT_ZIP,
            "attestation_path": self.attestation,
            "output_root": self.output,
            "packet": self.packet,
            "estimated_gpu_seconds": 14_000,
            "estimated_output_bytes": 13_000_000_000,
            "now": NOW,
            "authenticated_evidence_verifier": lambda _attested, _path: True,
        }

    def test_stale_or_insufficient_provider_attestation_fails(self) -> None:
        self.write_attestation(observed=NOW - timedelta(minutes=21))
        with self.assertRaisesRegex(ValueError, "stale/future"):
            _attestation(ROOT, self.attestation, NOW, 14_000, 13_000_000_000)
        self.write_attestation(gpu_seconds=17_000)
        with self.assertRaisesRegex(ValueError, "insufficient"):
            _attestation(ROOT, self.attestation, NOW, 14_000, 13_000_000_000)
        self.write_attestation(provider_bytes=12_000_000_000)
        with self.assertRaisesRegex(ValueError, "insufficient"):
            _attestation(ROOT, self.attestation, NOW, 14_000, 13_000_000_000)
        self.write_attestation(provider_bytes=13_000_000_000 + MIN_FREE_BYTES - 1)
        with self.assertRaisesRegex(ValueError, "insufficient"):
            _attestation(ROOT, self.attestation, NOW, 14_000, 13_000_000_000)
        self.assertFalse(self.packet.exists())

    def test_candidate_code_shortfall_and_drift_guards(self) -> None:
        self.assertEqual(len(_candidate(ROOT, CANDIDATE, self.analysis, SOURCES)[0]["jobs"]), 360)
        self.spec["executed_hung_code_sha256"]["model.py"] = "0" * 64
        write_json(self.analysis, self.spec)
        with self.assertRaisesRegex(ValueError, "Changed candidate code"):
            _candidate(ROOT, CANDIDATE, self.analysis, SOURCES)
        self.spec["executed_hung_code_sha256"]["model.py"] = _pin(
            ROOT / "experiments/hung_sprint2/model.py"
        )["sha256"]
        changed = self.base / "changed-candidate"
        changed.mkdir()
        for name in (
            "candidate_jobset.json",
            "candidate_execution_plan.json",
            "candidate_coverage.json",
            "source_config_bindings.json",
        ):
            (changed / name).write_bytes((CANDIDATE / name).read_bytes())
        with (changed / "candidate_jobset.json").open("a", encoding="utf-8") as stream:
            stream.write(" ")
        write_json(self.analysis, self.spec)
        with self.assertRaisesRegex(ValueError, "Candidate or analysis identity changed"):
            _candidate(ROOT, changed, self.analysis, SOURCES)
        (changed / "candidate_jobset.json").write_bytes(
            (CANDIDATE / "candidate_jobset.json").read_bytes()
        )
        coverage = json.loads((changed / "candidate_coverage.json").read_text())
        coverage["declared_shortfalls"] = []
        write_json(changed / "candidate_coverage.json", coverage)
        write_json(self.analysis, self.spec)
        with self.assertRaisesRegex(ValueError, "shortfalls"):
            _candidate(ROOT, changed, self.analysis, SOURCES)
        plan = json.loads((changed / "candidate_execution_plan.json").read_text())
        next(row for row in plan["jobs"] if row["method"] == "drift")["replay"][
            "drift_reference_mean"
        ] = 1.0
        write_json(changed / "candidate_execution_plan.json", plan)
        self.spec["authority"]["candidate_execution_plan_sha256"] = _pin(
            changed / "candidate_execution_plan.json"
        )["sha256"]
        coverage["declared_shortfalls"] = json.loads(
            (CANDIDATE / "candidate_coverage.json").read_text()
        )["declared_shortfalls"]
        write_json(changed / "candidate_coverage.json", coverage)
        write_json(self.analysis, self.spec)
        with self.assertRaisesRegex(ValueError, "Drift"):
            _candidate(ROOT, changed, self.analysis, SOURCES)

    def test_budget_and_local_reserve_gate_precede_creation(self) -> None:
        args = self.args()
        args["estimated_output_bytes"] = 1_000_000
        with self.assertRaisesRegex(ValueError, "understates"):
            prepare_lock(**args)
        self.assertFalse(self.packet.exists())
        args = self.args()
        args["authenticated_evidence_verifier"] = None
        with self.assertRaisesRegex(ValueError, "not independently verified"):
            prepare_lock(**args)
        self.assertFalse(self.packet.exists())
        with mock.patch("tools.hung_final_lock_preflight.shutil.disk_usage") as usage:
            usage.return_value.free = 1
            with self.assertRaisesRegex(ValueError, "Local Final lock staging space"):
                prepare_lock(**self.args())
        self.assertFalse(self.packet.exists())

    def test_synthetic_attestation_creates_lock_once_without_final_access(self) -> None:
        args = self.args()
        with (
            mock.patch("tools.hung_final_lock_preflight.shutil.disk_usage") as usage,
            mock.patch("tools.hung_final_lock_preflight._code_commit", return_value="a" * 40),
        ):
            usage.return_value.free = 50_000_000_000
            result = prepare_lock(**args)
        lock = json.loads(Path(result["lock"]).read_text(encoding="utf-8"))
        self.assertEqual(lock["schema"], "hung-final-lock-v1")
        self.assertEqual(lock["jobset"]["count"], 360)
        self.assertEqual(lock["authorization"]["comment_id"], 6476049006)
        self.assertEqual(lock["drift_reference"]["scale_floor"], 0.1)
        self.assertEqual(lock["resources"]["estimated_output_bytes"], 13_000_000_000)
        self.assertTrue(
            all(
                not Path(lock[key]["path"]).is_absolute()
                for key in ("input", "jobset", "execution_plan", "analysis")
            )
        )
        self.assertTrue(
            all(not Path(row["path"]).is_absolute() for row in lock["source_checkpoints"])
        )
        self.assertFalse(Path(lock["output_root"]).is_absolute())
        self.assertEqual(_pin(Path(result["lock"]))["sha256"], result["sha256"])
        self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(ValueError, "must be new"):
            prepare_lock(**args)

    def test_lock_references_validate_after_checkout_relocation(self) -> None:
        with (
            mock.patch("tools.hung_final_lock_preflight.shutil.disk_usage") as usage,
            mock.patch("tools.hung_final_lock_preflight._code_commit", return_value="a" * 40),
        ):
            usage.return_value.free = 50_000_000_000
            result = prepare_lock(**self.args())
        lock = json.loads(Path(result["lock"]).read_text(encoding="utf-8"))
        relocated = self.base / "relocated-checkout"
        refs = [lock[key] for key in ("input", "jobset", "execution_plan", "analysis")]
        refs += lock["source_checkpoints"]
        refs += [{"path": Path(result["lock"]).relative_to(ROOT).as_posix()}]
        for ref in refs:
            original = ROOT / ref["path"]
            destination = relocated / ref["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.link(original, destination)
        with mock.patch("experiments.hung_sprint2.final_lock.ROOT", relocated):
            context = validate_lock(
                relocated / Path(result["lock"]).relative_to(ROOT),
                result["sha256"],
                check_code=False,
                verify_input_runs=False,
            )
        self.assertEqual(len(context["jobs"]), 360)
        self.assertEqual(context["coverage_status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
