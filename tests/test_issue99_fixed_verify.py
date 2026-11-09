"""Independent Fixed calibration artifact and metric verification fixtures."""

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from ev_models.checkpoint import digest
from ev_runner.replay import Labels
from ev_runner.state import state_digest
from ev_search.execute import SEEDS, TARGETS
from ev_search.fixed import FixedSearchConfig
from ev_search.fixed_verify import (
    RUNNER_FILES,
    SCORER_COMMIT,
    SCORER_FILES,
    _code_hashes,
    verify_fixed_trials,
)
from ev_search.ledger import FixedLedger
from ev_search.protocol import canonical_sha256


class FakeInputs:
    sha256 = "a" * 64
    source_hash = "b" * 64

    def binding(self, stage, target, source_sha):
        return {"stage": stage, "target": target, "source": source_sha}


class FakeReplay:
    start = datetime.fromisoformat("2023-01-03T00:00:00+08:00")
    stop = start + timedelta(days=90)
    delay = timedelta(0)
    scale = 1.0

    def __init__(self, inputs, target, days):
        assert days == 90 and target in TARGETS

    def labels(self, origin, as_of):
        available = origin + timedelta(days=1)
        if as_of < available:
            return Labels("pending", None, available)
        return Labels("complete", (0.0,) * 24, available)


def fixture(
    root: Path,
    *,
    null_target: str | None = None,
    wrong_score: bool = False,
    complete: bool = False,
):
    scorer = root / "scorer"
    for folder in ("ev_search", "ev_inputs", "ev_models", "ev_control", "ev_runner", "configs"):
        (scorer / folder).mkdir(parents=True)
    for name in SCORER_FILES | RUNNER_FILES:
        (scorer / name).write_text(name)
    commit = SCORER_COMMIT
    (scorer / ".issue99-code-commit").write_text(commit + "\n")
    search = {
        "positive_lower": 0.1,
        "positive_upper": 1.0,
        "maximum_upper": 1.0,
        "expansion_factor": 2.0,
        "boundary_fraction": 0.1,
        "maximum_expansions": 0,
        "bo_trials": 1,
        "initial_lambdas": [0.1],
        "sensitivity_points": 2,
        "acquisition_grid_points": 16,
        "kernel_length": 1.0,
        "signal_std": 0.1,
        "noise_std": 0.01,
        "expected_improvement_jitter": 0.001,
    }
    search_path = scorer / "configs/issue99-fixed-search-v1.json"
    search_path.write_text(json.dumps(search))
    study = {
        "phase": "calibration",
        "frozen_lambda": True,
        "initial_training": {"seed": 42},
        "online_training": {"seed": 42},
        "diagnostics": {"cadence": 7, "epsilon_g": 1e-12},
    }
    (scorer / "configs/issue99-study-calibration-v1.json").write_text(json.dumps(study))
    sources = {}
    for seed in SEEDS:
        path = root / f"source-{seed}.pt"
        path.write_text(str(seed))
        sources[str(seed)] = {"path": str(path), "sha256": digest(path)}
    origins = {target: [FakeReplay.start.isoformat()] for target in TARGETS}
    protocol = root / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "status": "locked_owner_approved",
                "code_commit": commit,
                "input_manifest_sha256": FakeInputs.sha256,
                "source_population_sha256": FakeInputs.source_hash,
                "source_checkpoint_sha256": {
                    seed: source["sha256"] for seed, source in sources.items()
                },
                "fixed_search_config_sha256": digest(search_path),
                "calibration_study_template_sha256": canonical_sha256(study),
                "calibration_origins": origins,
                "minimum_scored_days": {"calibration": {target: 1 for target in TARGETS}},
                "diagnostics": study["diagnostics"],
            }
        )
    )
    binding = {
        "schema": "issue99-fixed-calibration-binding-v1",
        "input_manifest_sha256": FakeInputs.sha256,
        "source_population_sha256": FakeInputs.source_hash,
        "protocol_sha256": digest(protocol),
        "calibration_study_template_sha256": canonical_sha256(study),
        "fixed_search_config_sha256": digest(search_path),
        "code_commit": commit,
        "sources": {seed: source["sha256"] for seed, source in sources.items()},
        "code_files": _code_hashes(scorer, dict.fromkeys(SCORER_FILES, ""), SCORER_FILES),
        "runner_code_files": _code_hashes(
            scorer,
            dict.fromkeys(RUNNER_FILES, ""),
            RUNNER_FILES,
        ),
    }
    ledger = FixedLedger(root / "ledger", FixedSearchConfig(**search), binding=binding)

    def evaluate(weight, role, trial):
        trial_root = ledger.root / f"trial-{trial:04d}"
        trial_root.mkdir()
        rows = []
        for target in TARGETS:
            for seed in SEEDS:
                run = trial_root / f"target-{target}-seed-{seed}"
                run.mkdir()
                config = copy.deepcopy(study)
                config["initial_lambda"] = weight
                config["protocol_sha256"] = digest(protocol)
                config["objective_origins"] = origins[target]
                config["initial_training"]["seed"] = seed
                config["online_training"]["seed"] = seed
                run_binding = {
                    "input": FakeInputs().binding("target", target, sources[str(seed)]["sha256"]),
                    "source_population_sha256": FakeInputs.source_hash,
                    "code": {"commit": commit, "files": binding["runner_code_files"]},
                    "config": config,
                    "initial_adaptation_sha256": state_digest([]),
                }
                (run / "binding.json").write_text(json.dumps(run_binding))
                (run / "initial-adaptation.json").write_text("[]")
                previous = "0" * 64
                prediction_sha = ""
                is_null = target == null_target
                for index in range(2):
                    tick = run / f"tick-{index:04d}"
                    tick.mkdir()
                    forecast = (
                        {"origin": FakeReplay.start.isoformat(), "prediction": [2.0] * 24}
                        if index == 0
                        else {}
                    )
                    (tick / "forecasts.json").write_text(json.dumps(forecast))
                    if index == 0:
                        prediction_sha = digest(tick / "forecasts.json")
                        events = [
                            {
                                "event": "forecast_saved",
                                "origin": forecast["origin"],
                                "prediction_sha256": prediction_sha,
                            }
                        ]
                    else:
                        events = (
                            []
                            if is_null
                            else [
                                {
                                    "event": "score",
                                    "origin": FakeReplay.start.isoformat(),
                                    "as_of": (FakeReplay.start + timedelta(days=1)).isoformat(),
                                    "prediction_sha256": prediction_sha,
                                    "mae_kwh": 3.0 if wrong_score else 2.0,
                                    "mse_kwh2": 4.0,
                                }
                            ]
                        )
                    (tick / "events.jsonl").write_text(
                        "".join(json.dumps(event) + "\n" for event in events)
                    )
                    (tick / "state.pt").write_bytes(b"fixture")
                    meta = {
                        "index": index,
                        "previous": previous,
                        "files": {
                            name: digest(tick / name)
                            for name in ("state.pt", "events.jsonl", "forecasts.json")
                        },
                    }
                    (tick / "commit.json").write_text(json.dumps(meta))
                    previous = digest(tick / "commit.json")
                mae = None if is_null else 2.0
                report = {
                    "schema": "issue99-run-v1",
                    "run_id": run.name,
                    "phase": "calibration",
                    "method": "fixed_real_lambda",
                    "binding": run_binding,
                    "initial_logs": [],
                    "scheduled_days": 90,
                    "issued_days": 1,
                    "scored_days": 0 if is_null else 1,
                    "objective_requested_days": 1,
                    "objective_scored_days": 0 if is_null else 1,
                    "objective_minimum_scored_days": 1,
                    "objective_missing_origins": origins[target] if is_null else [],
                    "objective_coverage_pass": not is_null,
                    "mae_kwh": mae,
                    "rmse_kwh": mae,
                    "controller_decisions": 0,
                    "virtual_steps": 0,
                    "final_lambda": weight,
                    "commit_chain": previous,
                }
                (run / "run.json").write_text(json.dumps(report))
                rows.append(
                    {
                        "target": target,
                        "seed": seed,
                        "mae_kwh": mae,
                        "objective_scored_days": 0 if is_null else 1,
                        "objective_missing_origins": origins[target] if is_null else [],
                        "run_path": str(run),
                        "run_sha256": digest(run / "run.json"),
                    }
                )
        reasons = [f"{null_target}:coverage_or_failed_run"] if null_target else []
        stations = {target: (None if target == null_target else 2.0) for target in TARGETS}
        return {
            "objective_mae_kwh": None if null_target else 2.0,
            "station_first_mae_kwh": stations,
            "null_reasons": reasons,
            "role": role,
            "trial": trial,
            "lambda": weight,
            "runs": rows,
        }

    ledger.evaluate(0.0, "zero_baseline", evaluate)
    if complete:
        ledger.evaluate(0.1, "initial", evaluate)
        ledger.evaluate(1.0, "sensitivity", evaluate)
    return ledger.root, protocol, scorer, sources


class FixedVerifyTests(unittest.TestCase):
    def test_authenticates_runs_and_recomputes_station_first_score(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger, protocol, scorer, sources = fixture(Path(temporary))
            (scorer / "ev_search/fixed_verify.py").write_text("added after scorer commit")
            before = digest(ledger / "events.jsonl")
            with mock.patch("ev_search.fixed_verify.Replay", FakeReplay):
                result = verify_fixed_trials(ledger, FakeInputs(), protocol, scorer, sources)
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertFalse(result["search_complete"])
            self.assertEqual(result["verified_objectives"], 1)
            self.assertEqual(result["trials"][0]["objective_mae_kwh"], 2.0)
            self.assertEqual(digest(ledger / "events.jsonl"), before)

    def test_complete_search_passes_and_all_null_does_not(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger, protocol, scorer, sources = fixture(Path(temporary), complete=True)
            with mock.patch("ev_search.fixed_verify.Replay", FakeReplay):
                result = verify_fixed_trials(ledger, FakeInputs(), protocol, scorer, sources)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["verified_objectives"], 3)
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger, protocol, scorer, sources = fixture(
                Path(temporary), complete=True, null_target="1405"
            )
            with mock.patch("ev_search.fixed_verify.Replay", FakeReplay):
                result = verify_fixed_trials(ledger, FakeInputs(), protocol, scorer, sources)
            self.assertEqual(result["status"], "NO_VERIFIED_OBJECTIVE")
            self.assertEqual(result["verified_objectives"], 0)

    def test_null_coverage_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger, protocol, scorer, sources = fixture(Path(temporary), null_target="1405")
            with mock.patch("ev_search.fixed_verify.Replay", FakeReplay):
                result = verify_fixed_trials(ledger, FakeInputs(), protocol, scorer, sources)
            self.assertEqual(result["trials"][0]["status"], "null")
            self.assertIsNone(result["trials"][0]["objective_mae_kwh"])

    def test_failed_trial_without_run_directory_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger_root, protocol, scorer, sources = fixture(Path(temporary))
            search = FixedSearchConfig(
                **json.loads((scorer / "configs/issue99-fixed-search-v1.json").read_text())
            )
            ledger = FixedLedger(
                ledger_root,
                search,
                binding=json.loads((ledger_root / "config.json").read_text())["binding"],
                resume=True,
            )
            ledger.evaluate(0.1, "initial", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
            with mock.patch("ev_search.fixed_verify.Replay", FakeReplay):
                result = verify_fixed_trials(ledger_root, FakeInputs(), protocol, scorer, sources)
            self.assertEqual(result["trials"][1]["status"], "failed")
            self.assertIsNone(result["trials"][1]["objective_mae_kwh"])

    def test_rejects_wrong_saved_score_even_with_valid_hash_chain(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger, protocol, scorer, sources = fixture(Path(temporary), wrong_score=True)
            with self.assertRaisesRegex(ValueError, "score differs from forecast and labels"):
                with mock.patch("ev_search.fixed_verify.Replay", FakeReplay):
                    verify_fixed_trials(ledger, FakeInputs(), protocol, scorer, sources)

    def test_rejects_tampered_scorer_code_or_run_bytes(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger, protocol, scorer, sources = fixture(Path(temporary))
            (scorer / "ev_search/execute.py").write_text("changed")
            with self.assertRaisesRegex(ValueError, "binding differs"):
                verify_fixed_trials(ledger, FakeInputs(), protocol, scorer, sources)
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            _, _, scorer, _ = fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError, "inventory differs"):
                _code_hashes(
                    scorer, dict.fromkeys(SCORER_FILES - {"ev_search/execute.py"}, ""), SCORER_FILES
                )
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger, protocol, scorer, sources = fixture(Path(temporary))
            victim = ledger / "trial-0000/target-1405-seed-42/tick-0000/forecasts.json"
            victim.write_text(victim.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "Changed committed tick artifact"):
                with mock.patch("ev_search.fixed_verify.Replay", FakeReplay):
                    verify_fixed_trials(ledger, FakeInputs(), protocol, scorer, sources)


if __name__ == "__main__":
    unittest.main()
