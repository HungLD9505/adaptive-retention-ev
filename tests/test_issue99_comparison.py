"""Hash-bound paired comparison planning and exact-reuse fixtures."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from ev_models.checkpoint import digest
from ev_runner.continuous_run import code_identity as continuous_code_identity
from ev_runner.replay import Labels
from ev_runner.run import runtime_code as discrete_code_identity
from ev_search.comparison import event_hashes, execute_job, plan_jobs
from ev_search.comparison_verify import verify_matrix

TARGETS = ("1405", "2152", "1153", "1693")


class FakeInputs:
    target_role = "development"
    config = {"history_days": 14}
    sha256 = "a" * 64
    source_hash = "b" * 64
    namespace = ("urban", "sz")
    entities = {("urban", "sz", target): {"scale": {"energy_scale": 1.0}} for target in TARGETS}

    def binding(self, stage, target, source_sha):
        return {"stage": stage, "target": target, "source": source_sha}


class FakeReplay:
    scale = 1.0

    def __init__(self, inputs, target, days):
        assert days == 90

    def labels(self, origin, as_of):
        available = origin + timedelta(days=2)
        if as_of < available:
            return Labels("pending", None, available)
        return Labels("complete", (0.0,) * 24, available)


def fixtures(root, *, fixed=0.5, initial=0.5):
    origins = {target: ["2023-01-03T00:00:00+08:00"] for target in TARGETS}
    protocol_path = root / "protocol.json"
    protocol_path.write_text(
        json.dumps(
            {
                "status": "locked_owner_approved",
                "owner_authorization": "fixture-approved",
                "input_manifest_sha256": "a" * 64,
                "source_population_sha256": "b" * 64,
                "evaluation_origins": origins,
                "minimum_scored_days": {"evaluation": {target: 1 for target in TARGETS}},
            }
        )
    )
    training = {
        "seed": 42,
        "epochs": 1,
        "batch_size": 1,
        "learning_rate": 0.001,
        "epsilon": 0.001,
        "head_width": 64,
    }
    study = {
        "schema": "issue99-study-v1",
        "phase": "evaluation",
        "targets": list(TARGETS),
        "replay_days": 90,
        "initial_training": training,
        "online_training": dict(training),
        "window_rule": {
            "older_count": 1,
            "newer_count": 1,
            "upper_bound": 2.0,
            "meta_step_size": 0.01,
            "epsilon": 0.001,
        },
        "cadence": 1,
        "frozen_lambda": False,
        "initial_lambda": 0.0,
        "objective_origins": [],
        "protocol_sha256": "",
    }
    discrete = {
        "method": {"name": "adaptive"},
        "replay_days": 90,
        "initial_training": dict(training),
        "online_training": dict(training),
        "controller": {"seed": 42},
        "development_entities": list(TARGETS),
    }
    lock_path = root / "lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "schema": "issue99-comparison-lock-v1",
                "status": "locked_owner_approved",
                "protocol_sha256": digest(protocol_path),
                "selected_fixed_lambda": fixed,
                "controller_initial_lambda": initial,
                "study_template": study,
                "discrete_config": discrete,
            }
        )
    )
    sources = {}
    for seed in (42, 43, 44):
        source = root / f"seed-{seed}.pt"
        source.write_text(str(seed))
        sources[str(seed)] = {"path": str(source), "sha256": digest(source)}
    return protocol_path, lock_path, sources


class ComparisonTests(unittest.TestCase):
    def test_plan_sixty_identities_and_only_exact_frozen_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, lock, sources = fixtures(root)
            jobs = plan_jobs(FakeInputs(), protocol, lock, sources)
            self.assertEqual(len(jobs), 60)
            frozen = [job for job in jobs if job["method"] == "frozen_lambda"]
            self.assertEqual(len(frozen), 12)
            self.assertTrue(
                all(
                    job["reuse_job_id"] == f"fixed-{job['target']}-seed{job['seed']}"
                    for job in frozen
                )
            )
            _, different_lock, sources = fixtures(root, fixed=0.5, initial=0.4)
            jobs = plan_jobs(FakeInputs(), protocol, different_lock, sources)
            self.assertTrue(
                all(job["reuse_job_id"] is None for job in jobs if job["method"] == "frozen_lambda")
            )

    def test_reject_final_input_and_changed_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, lock, sources = fixtures(root)
            inputs = FakeInputs()
            inputs.target_role = "final"
            with self.assertRaisesRegex(ValueError, "Final is excluded"):
                plan_jobs(inputs, protocol, lock, sources)
            lock_data = json.loads(lock.read_text())
            lock_data["protocol_sha256"] = "changed"
            lock.write_text(json.dumps(lock_data))
            with self.assertRaisesRegex(ValueError, "matching owner-locked"):
                plan_jobs(FakeInputs(), protocol, lock, sources)

    def test_execute_exact_alias_checks_binding_and_preserves_source_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, lock, sources = fixtures(root)
            jobs = plan_jobs(FakeInputs(), protocol, lock, sources)
            fixed = next(
                job
                for job in jobs
                if job["method"] == "fixed" and job["target"] == "1405" and job["seed"] == 42
            )
            frozen = next(
                job
                for job in jobs
                if job["method"] == "frozen_lambda"
                and job["target"] == "1405"
                and job["seed"] == 42
            )
            output = root / "runs"
            code = continuous_code_identity()["files"]

            def fake_run(inputs, target, source_path, source_sha, config, run_root, **kwargs):
                run_root.mkdir()
                report = {
                    "phase": "evaluation",
                    "binding": {
                        "input": inputs.binding("target", target, source_sha),
                        "config": config,
                        "source_population_sha256": inputs.source_hash,
                        "code": {"files": code},
                    },
                }
                (run_root / "run.json").write_text(json.dumps(report))
                return report

            with mock.patch(
                "ev_search.comparison.execute_continuous", side_effect=fake_run
            ) as patched:
                first = execute_job(fixed, FakeInputs(), protocol, lock, output, device="cpu")
                reused = execute_job(frozen, FakeInputs(), protocol, lock, output, device="cpu")
            self.assertEqual(patched.call_count, 1)
            self.assertEqual(first["run_sha256"], reused["run_sha256"])
            self.assertEqual(reused["reused_from"], fixed["job_id"])
            with self.assertRaises(FileExistsError):
                execute_job(frozen, FakeInputs(), protocol, lock, output, device="cpu")

    def test_verify_saved_matrix_recomputes_common_origin_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, lock, sources = fixtures(root)
            inputs = FakeInputs()
            jobs = plan_jobs(inputs, protocol, lock, sources)
            output = root / "runs"
            for job in jobs:
                run = output / job["job_id"] / "run"
                tick = run / "tick-0000"
                tick.mkdir(parents=True)
                origin = job["evaluation_origins"][0]
                forecast = {
                    "origin": origin,
                    "prediction": [2.0] * 24,
                    "predictions": [[2.0] * 24],
                    "active": 0.0,
                }
                (tick / "forecasts.json").write_text(json.dumps(forecast))
                event = {
                    "event": "score",
                    "origin": origin,
                    "as_of": (datetime.fromisoformat(origin) + timedelta(days=2)).isoformat(),
                    "prediction_sha256": digest(tick / "forecasts.json"),
                    "mae_kwh": 2.0,
                    "mse_kwh2": 4.0,
                    "mae_scaled": [2.0],
                    "mse_scaled": [4.0],
                    "issued_active": 0.0,
                }
                (tick / "events.jsonl").write_text(json.dumps(event) + "\n")
                (tick / "state.pt").write_bytes(b"fixture-state")
                commit = {
                    "index": 0,
                    "previous": "0" * 64,
                    "files": {
                        name: digest(tick / name)
                        for name in ("state.pt", "events.jsonl", "forecasts.json")
                    },
                }
                (tick / "commit.json").write_text(json.dumps(commit))
                binding = {
                    "input": inputs.binding("target", job["target"], job["source_sha256"]),
                    "config": job["config"],
                    "source_population_sha256": inputs.source_hash,
                    "code": {"files": continuous_code_identity()["files"]},
                    "code_files": discrete_code_identity()["files"],
                }
                report = {
                    "binding": binding,
                    "commit_chain": digest(tick / "commit.json"),
                    "phase": "evaluation",
                    "scheduled_days": 90,
                    "issued_days": 1,
                    "scored_days": 1,
                    "candidate_levels": [0.0],
                    "objective_scored_days": 1,
                    "objective_missing_origins": [],
                    "objective_coverage_pass": True,
                    "mae_kwh": 2.0,
                    "rmse_kwh": 2.0,
                    "active_mae_kwh": 2.0,
                    "active_rmse_kwh": 2.0,
                }
                (run / "binding.json").write_text(json.dumps(binding))
                (run / "run.json").write_text(json.dumps(report))
                saved = {
                    "job": job,
                    "reused_from": job["reuse_job_id"],
                    "run_path": f"{job['job_id']}/run",
                    "run_sha256": digest(run / "run.json"),
                    "event_sha256": event_hashes(run),
                }
                (run.parent / "job.json").write_text(json.dumps(saved))
            # Avoid synthetic aliases in this fixture: production aliases must point to the same run.
            for job in jobs:
                if job["reuse_job_id"]:
                    saved_path = output / job["job_id"] / "job.json"
                    saved = json.loads(saved_path.read_text())
                    source_run = output / job["reuse_job_id"] / "run"
                    saved.update(
                        run_path=f"{job['reuse_job_id']}/run",
                        run_sha256=digest(source_run / "run.json"),
                        event_sha256=event_hashes(source_run),
                    )
                    saved_path.write_text(json.dumps(saved))
            with mock.patch("ev_search.comparison_verify.Replay", FakeReplay):
                result = verify_matrix(jobs, output, inputs, protocol)
            self.assertEqual(result["aggregate_mae_kwh"]["fixed"], 2.0)
            self.assertEqual(result["target_rmse_kwh"]["1405"]["fixed"], 2.0)
            self.assertEqual(result["paired_mae_delta_vs_lambda0_kwh"]["1405"]["fixed"]["42"], 0.0)
            victim = output / "lambda0-1405-seed42" / "run" / "tick-0000" / "events.jsonl"
            victim.write_text(victim.read_text().replace("2.0", "3.0"))
            with self.assertRaisesRegex(ValueError, "stream hash changed"):
                with mock.patch("ev_search.comparison_verify.Replay", FakeReplay):
                    verify_matrix(jobs, output, inputs, protocol)
            # A forged event with fresh hashes still cannot change the label/vector metric.
            run = victim.parent.parent
            score = json.loads(victim.read_text())
            score["mae_kwh"] = 3.0
            victim.write_text(json.dumps(score) + "\n")
            commit_path = victim.parent / "commit.json"
            commit = json.loads(commit_path.read_text())
            commit["files"]["events.jsonl"] = digest(victim)
            commit_path.write_text(json.dumps(commit))
            report_path = run / "run.json"
            report = json.loads(report_path.read_text())
            report["commit_chain"] = digest(commit_path)
            report_path.write_text(json.dumps(report))
            job_path = run.parent / "job.json"
            saved = json.loads(job_path.read_text())
            saved["run_sha256"] = digest(report_path)
            saved["event_sha256"] = event_hashes(run)
            job_path.write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError, "score differs from forecast and labels"):
                with mock.patch("ev_search.comparison_verify.Replay", FakeReplay):
                    verify_matrix(jobs, output, inputs, protocol)

    def test_resume_uses_fresh_output_and_rejects_changed_partial_chain(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, lock, sources = fixtures(root)
            inputs = FakeInputs()
            job = next(
                job
                for job in plan_jobs(inputs, protocol, lock, sources)
                if job["method"] == "continuous" and job["target"] == "1405" and job["seed"] == 42
            )
            old = root / "partial" / "run"
            tick = old / "tick-0000"
            tick.mkdir(parents=True)
            binding = {
                "input": inputs.binding("target", job["target"], job["source_sha256"]),
                "config": job["config"],
                "source_population_sha256": inputs.source_hash,
                "code": {"files": continuous_code_identity()["files"]},
            }
            (old / "binding.json").write_text(json.dumps(binding))
            for name in ("forecasts.json", "events.jsonl", "state.pt"):
                (tick / name).write_bytes(name.encode())
            commit = {
                "index": 0,
                "previous": "0" * 64,
                "files": {
                    name: digest(tick / name)
                    for name in ("state.pt", "events.jsonl", "forecasts.json")
                },
            }
            (tick / "commit.json").write_text(json.dumps(commit))
            old_hash = digest(tick / "commit.json")

            def fake_resume(*args, **kwargs):
                self.assertEqual(kwargs["resume_from"], old)
                run_root = args[5]
                run_root.mkdir()
                report = {"phase": "evaluation", "binding": binding}
                (run_root / "run.json").write_text(json.dumps(report))
                return report

            with mock.patch("ev_search.comparison.execute_continuous", side_effect=fake_resume):
                result = execute_job(
                    job, inputs, protocol, lock, root / "fresh", device="cpu", resume_from=old
                )
            self.assertEqual(result["resume_source_chain_sha256"], old_hash)
            self.assertEqual(digest(tick / "commit.json"), old_hash)
            (tick / "state.pt").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Resume committed artifact differs"):
                execute_job(
                    job, inputs, protocol, lock, root / "another", device="cpu", resume_from=old
                )
            self.assertFalse((root / "another").exists())


if __name__ == "__main__":
    unittest.main()
