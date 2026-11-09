"""Read-only, original-unit verification of issue #99 Fixed calibration runs."""

import argparse
import copy
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from ev_models.checkpoint import digest
from ev_models.data import InputRun
from ev_runner.replay import Replay
from ev_runner.state import state_digest
from ev_search.comparison_verify import _scores, _verify_commit_chain
from ev_search.execute import SEEDS, TARGETS
from ev_search.fixed import FixedSearchConfig
from ev_search.ledger import FixedLedger
from ev_search.protocol import canonical_sha256

DAY = timedelta(days=1)


def _same(actual: float | None, expected: float | None) -> bool:
    if actual is None or expected is None:
        return actual is expected
    return math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6)


def _code_hashes(root: Path, names: dict[str, str], folders: tuple[str, ...]) -> dict[str, str]:
    """Hash the scorer's recorded file set; verifier files can be added later."""
    allowed = {
        path.relative_to(root).as_posix()
        for folder in folders
        for path in (root / folder).glob("*.py")
    }
    if not names or not set(names) <= allowed:
        raise ValueError("Recorded scorer file set is missing from staged code")
    return {name: digest(root / name) for name in names}


def _verify_ledger(
    ledger_root: Path, protocol_path: Path, scorer_root: Path, inputs, sources: dict
) -> tuple[FixedLedger, dict, dict]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    metadata = json.loads((ledger_root / "config.json").read_text(encoding="utf-8"))
    search_path = scorer_root / "configs/issue99-fixed-search-v1.json"
    study_path = scorer_root / "configs/issue99-study-calibration-v1.json"
    study = json.loads(study_path.read_text(encoding="utf-8"))
    commit = (scorer_root / ".issue99-code-commit").read_text(encoding="ascii").strip()
    code_files = metadata["binding"]["code_files"]
    runner_files = metadata["binding"]["runner_code_files"]
    expected = {
        "schema": "issue99-fixed-calibration-binding-v1",
        "input_manifest_sha256": protocol["input_manifest_sha256"],
        "source_population_sha256": protocol["source_population_sha256"],
        "protocol_sha256": digest(protocol_path),
        "calibration_study_template_sha256": canonical_sha256(study),
        "fixed_search_config_sha256": digest(search_path),
        "code_commit": commit,
        "sources": protocol["source_checkpoint_sha256"],
        "code_files": _code_hashes(scorer_root, code_files, ("ev_search",)),
        "runner_code_files": _code_hashes(
            scorer_root, runner_files, ("ev_inputs", "ev_models", "ev_control", "ev_runner")
        ),
    }
    if (
        protocol.get("status") != "locked_owner_approved"
        or commit != protocol["code_commit"]
        or expected["fixed_search_config_sha256"] != protocol["fixed_search_config_sha256"]
        or expected["calibration_study_template_sha256"]
        != protocol["calibration_study_template_sha256"]
        or study.get("phase") != "calibration"
        or study.get("frozen_lambda") is not True
        or metadata.get("binding") != expected
        or inputs.sha256 != protocol["input_manifest_sha256"]
        or inputs.source_hash != protocol["source_population_sha256"]
    ):
        raise ValueError("Fixed ledger code/input/protocol binding differs")
    if set(sources) != {str(seed) for seed in SEEDS}:
        raise ValueError("Fixed verifier needs exactly three Source10 checkpoints")
    for seed, source in sources.items():
        if (
            source["sha256"] != protocol["source_checkpoint_sha256"][seed]
            or digest(Path(source["path"])) != source["sha256"]
        ):
            raise ValueError("Fixed Source10 checkpoint binding differs")
    config = FixedSearchConfig(**json.loads(search_path.read_text(encoding="utf-8")))
    return FixedLedger(ledger_root, config, binding=expected, resume=True), protocol, study


def _verify_run(
    run_path: Path,
    target: str,
    seed: int,
    weight: float,
    row: dict,
    inputs,
    protocol: dict,
    study: dict,
    runner_files: dict[str, str],
    replay: Replay,
    protocol_path: Path,
) -> dict:
    report_path = run_path / "run.json"
    if row["run_sha256"] != digest(report_path):
        raise ValueError("Fixed run report SHA-256 differs")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    binding = report["binding"]
    config = binding["config"]
    expected_config = copy.deepcopy(study)
    expected_config["initial_lambda"] = weight
    expected_config["protocol_sha256"] = digest(protocol_path)
    expected_config["objective_origins"] = protocol["calibration_origins"][target]
    expected_config["initial_training"]["seed"] = seed
    expected_config["online_training"]["seed"] = seed
    if (
        json.loads((run_path / "binding.json").read_text(encoding="utf-8")) != binding
        or report["schema"] != "issue99-run-v1"
        or report["phase"] != "calibration"
        or report["method"] != "fixed_real_lambda"
        or report["run_id"] != run_path.name
        or report["scheduled_days"] != 90
        or binding["input"]
        != inputs.binding("target", target, protocol["source_checkpoint_sha256"][str(seed)])
        or binding["source_population_sha256"] != inputs.source_hash
        or binding["code"]["commit"] != protocol["code_commit"]
        or binding["code"]["files"] != runner_files
        or config != expected_config
        or report["controller_decisions"] != 0
        or report["virtual_steps"] != 0
        or report["final_lambda"] != weight
    ):
        raise ValueError("Fixed run binding, method or frozen trajectory differs")
    initial_logs = json.loads((run_path / "initial-adaptation.json").read_text(encoding="utf-8"))
    if report["initial_logs"] != initial_logs or binding[
        "initial_adaptation_sha256"
    ] != state_digest(initial_logs):
        raise ValueError("Fixed initial adaptation logs differ from run binding")
    _verify_commit_chain(run_path, report)
    end = min(
        replay.stop + (int(replay.delay.total_seconds() // DAY.total_seconds()) + 1) * DAY,
        max(datetime.fromisoformat(origin) for origin in config["objective_origins"])
        + DAY
        + replay.delay,
    )
    expected_ticks = int((end - replay.start) // DAY) + 1
    if len(list(run_path.glob("tick-*"))) != expected_ticks:
        raise ValueError("Fixed calibration run ended before its declared horizon")
    issued, errors = _scores(run_path, {"family": "continuous"}, replay)
    requested = set(protocol["calibration_origins"][target])
    scored = requested & errors.keys()
    minimum = protocol["minimum_scored_days"]["calibration"][target]
    if len(requested) != len(protocol["calibration_origins"][target]) or not 1 <= minimum <= len(
        requested
    ):
        raise ValueError("Invalid registered Fixed calibration origins or coverage minimum")
    valid = len(scored) >= minimum
    mae = sum(errors[origin][0] for origin in scored) / len(scored) if valid else None
    rmse = math.sqrt(sum(errors[origin][1] for origin in scored) / len(scored)) if valid else None
    if (
        report["issued_days"] != len(issued)
        or report["scored_days"] != len(errors)
        or report["objective_requested_days"] != len(requested)
        or report["objective_scored_days"] != len(scored)
        or report["objective_minimum_scored_days"] != minimum
        or set(report["objective_missing_origins"]) != requested - scored
        or report["objective_coverage_pass"] != valid
        or not _same(report["mae_kwh"], mae)
        or not _same(report["rmse_kwh"], rmse)
        or row["objective_scored_days"] != len(scored)
        or set(row["objective_missing_origins"]) != requested - scored
        or not _same(row["mae_kwh"], mae)
    ):
        raise ValueError("Fixed run objective differs from authenticated forecast and labels")
    return {
        "target": target,
        "seed": seed,
        "mae_kwh": mae,
        "missing_origins": sorted(requested - scored),
    }


def verify_fixed_trials(
    ledger_root: Path, inputs, protocol_path: Path, scorer_root: Path, sources: dict
) -> dict:
    """Recompute every completed trial without using the scorer's saved aggregate."""
    ledger, protocol, study = _verify_ledger(
        ledger_root, protocol_path, scorer_root, inputs, sources
    )
    replays = {target: Replay(inputs, target, 90) for target in TARGETS}
    details = []
    for event in ledger.completed():
        outcome = event["outcome"]
        trial = event["trial"]
        trial_root = ledger_root / f"trial-{trial:04d}"
        if event["status"] == "failed":
            if outcome.get("objective_mae_kwh") is not None or not isinstance(
                outcome.get("error"), str
            ):
                raise ValueError("Failed Fixed trial lacks null objective or recorded error")
            details.append(
                {
                    "trial": trial,
                    "lambda": event["lambda"],
                    "status": "failed",
                    "objective_mae_kwh": None,
                }
            )
            continue
        if (
            outcome["trial"] != trial
            or outcome["role"] != event["role"]
            or outcome["lambda"] != event["lambda"]
            or len(outcome["runs"]) != len(TARGETS) * len(SEEDS)
        ):
            raise ValueError("Fixed trial run identities differ")
        rows = {}
        for row in outcome["runs"]:
            target, seed = row["target"], row["seed"]
            key = (target, seed)
            if target not in TARGETS or seed not in SEEDS or key in rows:
                raise ValueError("Duplicate or unexpected Fixed target/seed")
            run_path = trial_root / f"target-{target}-seed-{seed}"
            if Path(row["run_path"]).parts[-2:] != run_path.parts[-2:]:
                raise ValueError("Saved Fixed run path differs from trial identity")
            rows[key] = _verify_run(
                run_path,
                target,
                seed,
                event["lambda"],
                row,
                inputs,
                protocol,
                study,
                ledger.binding["runner_code_files"],
                replays[target],
                protocol_path,
            )
        if set(rows) != {(target, seed) for target in TARGETS for seed in SEEDS}:
            raise ValueError("Incomplete Fixed target/seed matrix")
        stations = {}
        null_reasons = []
        for target in TARGETS:
            station = [rows[target, seed] for seed in SEEDS]
            if len({tuple(row["missing_origins"]) for row in station}) != 1:
                raise ValueError("Fixed paired seeds scored different origins")
            values = [row["mae_kwh"] for row in station]
            if any(value is None for value in values):
                stations[target] = None
                null_reasons.append(f"{target}:coverage_or_failed_run")
            else:
                stations[target] = sum(values) / len(values)
        macro = sum(stations.values()) / len(TARGETS) if not null_reasons else None
        if (
            (event["status"] == "complete") != (macro is not None)
            or not _same(outcome["objective_mae_kwh"], macro)
            or outcome["null_reasons"] != null_reasons
            or any(
                not _same(outcome["station_first_mae_kwh"][target], stations[target])
                for target in TARGETS
            )
        ):
            raise ValueError("Fixed trial aggregate differs from independently verified runs")
        details.append(
            {
                "trial": trial,
                "lambda": event["lambda"],
                "status": event["status"],
                "objective_mae_kwh": macro,
                "station_first_mae_kwh": stations,
            }
        )
    return {
        "schema": "issue99-fixed-independent-verification-v1",
        "status": "PASS",
        "protocol_sha256": digest(protocol_path),
        "ledger_events_sha256": digest(ledger_root / "events.jsonl"),
        "code_commit": protocol["code_commit"],
        "trials": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--scorer-root", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    args = parser.parse_args()
    inputs = InputRun(args.inputs, args.manifest_sha256)
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    print(
        json.dumps(
            verify_fixed_trials(args.ledger, inputs, args.protocol, args.scorer_root, sources),
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
