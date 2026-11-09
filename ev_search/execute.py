"""Bounded Fixed calibration dispatcher over paired Source10 seeds and targets."""

import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path

from ev_models.checkpoint import digest
from ev_models.data import InputRun
from ev_runner.continuous_run import code_identity as runner_code_identity
from ev_runner.continuous_run import execute
from ev_search.fixed import FixedSearchConfig
from ev_search.ledger import FixedLedger, run_bounded_search

TARGETS = ("1405", "2152", "1153", "1693")
SEEDS = (42, 43, 44)
ROOT = Path(__file__).resolve().parents[1]


def aggregate_matrix(rows: list[dict]) -> dict:
    """Average paired seeds within station, then give four stations equal weight."""
    by_target = defaultdict(dict)
    for row in rows:
        target, seed = row["target"], row["seed"]
        if target not in TARGETS or seed not in SEEDS or seed in by_target[target]:
            raise ValueError("Duplicate or unexpected Fixed matrix identity")
        by_target[target][seed] = row
    if any(set(by_target[target]) != set(SEEDS) for target in TARGETS):
        raise ValueError("Incomplete Fixed matrix identity")
    station_scores = {}
    null_reasons = []
    for target in TARGETS:
        station = by_target[target]
        patterns = {tuple(station[seed]["objective_missing_origins"]) for seed in SEEDS}
        if len(patterns) != 1:
            raise ValueError("Paired seeds scored different target origins")
        values = [station[seed]["mae_kwh"] for seed in SEEDS]
        if any(value is None for value in values):
            null_reasons.append(f"{target}:coverage_or_failed_run")
            station_scores[target] = None
        else:
            station_scores[target] = sum(values) / len(values)
    score = sum(station_scores.values()) / len(TARGETS) if not null_reasons else None
    return {
        "objective_mae_kwh": score,
        "station_first_mae_kwh": station_scores,
        "null_reasons": null_reasons,
    }


class FixedMatrixEvaluator:
    def __init__(
        self,
        inputs: InputRun,
        protocol_path: Path,
        study_template: dict,
        sources: dict,
        output: Path,
        *,
        device: str,
    ) -> None:
        self.inputs = inputs
        self.protocol_path = protocol_path
        self.protocol = json.loads(protocol_path.read_text())
        self.protocol_sha256 = digest(protocol_path)
        self.study_template = study_template
        self.sources = sources
        self.output = output
        self.device = device
        if set(sources) != {str(seed) for seed in SEEDS}:
            raise ValueError("Exactly three Source10 seed bindings required")
        if self.protocol.get("status") != "locked_owner_approved":
            raise ValueError("Fixed search requires owner-locked protocol")
        if (
            study_template.get("phase") != "calibration"
            or study_template.get("frozen_lambda") is not True
        ):
            raise ValueError("Fixed search may execute calibration with frozen lambda only")

    def __call__(self, weight: float, role: str, trial: int) -> dict:
        trial_root = self.output / f"trial-{trial:04d}"
        trial_root.mkdir(exist_ok=False)
        rows = []
        for target in TARGETS:
            for seed in SEEDS:
                config = copy.deepcopy(self.study_template)
                config["initial_lambda"] = weight
                config["protocol_sha256"] = self.protocol_sha256
                config["objective_origins"] = self.protocol["calibration_origins"][target]
                config["initial_training"]["seed"] = seed
                config["online_training"]["seed"] = seed
                source = self.sources[str(seed)]
                run_root = trial_root / f"target-{target}-seed-{seed}"
                report = execute(
                    self.inputs,
                    target,
                    Path(source["path"]),
                    source["sha256"],
                    config,
                    run_root,
                    device=self.device,
                    protocol_path=self.protocol_path,
                )
                rows.append(
                    {
                        "target": target,
                        "seed": seed,
                        "mae_kwh": report["mae_kwh"],
                        "objective_scored_days": report["objective_scored_days"],
                        "objective_missing_origins": report["objective_missing_origins"],
                        "run_path": str(run_root),
                        "run_sha256": digest(run_root / "run.json"),
                        "invocation_wall_seconds": report["invocation_wall_seconds"],
                    }
                )
        summary = aggregate_matrix(rows)
        return {**summary, "role": role, "trial": trial, "lambda": weight, "runs": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "inputs",
        "manifest-sha256",
        "protocol",
        "study-template",
        "search-config",
        "sources",
        "output",
    ):
        parser.add_argument(
            "--" + name, required=True, type=Path if name != "manifest-sha256" else str
        )
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--max-new-trials", type=int, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    inputs = InputRun(args.inputs, args.manifest_sha256)
    search = FixedSearchConfig(**json.loads(args.search_config.read_text()))
    study = json.loads(args.study_template.read_text())
    sources = json.loads(args.sources.read_text())
    evaluator = FixedMatrixEvaluator(
        inputs, args.protocol, study, sources, args.output, device=args.device
    )
    binding = {
        "schema": "issue99-fixed-calibration-binding-v1",
        "input_manifest_sha256": inputs.sha256,
        "source_population_sha256": inputs.source_hash,
        "protocol_sha256": evaluator.protocol_sha256,
        "study_template_sha256": digest(args.study_template),
        "sources": {seed: source["sha256"] for seed, source in sources.items()},
        "code_files": {
            str(path.relative_to(ROOT)): digest(path)
            for path in sorted((ROOT / "ev_search").glob("*.py"))
        },
        "runner_code_files": runner_code_identity()["files"],
    }
    ledger = FixedLedger(args.output, search, binding=binding, resume=args.resume)
    results = run_bounded_search(ledger, evaluator, max_new_trials=args.max_new_trials)
    print(
        json.dumps(
            {
                "new_trials": len(results),
                "total_trials": len(ledger.completed()),
                "ledger_sha256": digest(args.output / "events.jsonl"),
            },
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
