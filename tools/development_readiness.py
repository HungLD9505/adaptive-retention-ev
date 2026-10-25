"""GPU-only multi-seed Development readiness; no tuning, Final or winner claims."""

import argparse
import copy
import json
import os
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

from ev_models.checkpoint import digest, write_json
from ev_runner.replay import Replay
from ev_runner.run import execute
from tools.comparison_matrix import CachedInputs


def validate_cohort(inputs: dict[int, CachedInputs], cohort: dict) -> None:
    if cohort["namespace"] != "urbanev-SZH" or cohort["methods"] != ["adaptive", "target_only"]:
        raise ValueError("Only the explicit UrbanEV paired-readiness scope is supported")
    if (
        cohort["seeds"] != [42, 43, 44]
        or cohort["days"] != 90
        or cohort["state_retention"] != "latest"
    ):
        raise ValueError("Unexpected declared readiness profile")
    if set(cohort["budgets"]) != {"7", "14", "28"}:
        raise ValueError("All history budgets required")
    if len({x.source_hash for x in inputs.values()}) != 1:
        raise ValueError("Budget Source populations differ")
    for budget, data in inputs.items():
        group = cohort["budgets"][str(budget)]
        if group["manifest_sha256"] != data.sha256:
            raise ValueError("Selection input fingerprint differs")
        ids = [r["entity_id"] for r in group["entities"]]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Nonempty unique cohort required")
        for item in group["entities"]:
            row = data.entities.get((*data.namespace, item["entity_id"]), {})
            if row.get("role") != "development" or row.get("status") != "ready":
                raise ValueError("Only ready Development targets are allowed")
            if row["initial_trainable"] != item["initial_trainable"]:
                raise ValueError("Prefix selection metadata differs")


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise ValueError("Real-data readiness requires a Colab CUDA runtime")
    if (
        digest(args.selection) != args.selection_sha256
        or digest(args.source_pool) != args.source_pool_sha256
    ):
        raise ValueError("Cohort/Source pool hash mismatch")
    cohort = json.loads(args.selection.read_text())
    data = {
        b: CachedInputs(
            args.inputs_root / f"urbanev-SZH-{b}d", cohort["budgets"][str(b)]["manifest_sha256"]
        )
        for b in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    pool = json.loads(args.source_pool.read_text())
    if pool["status"] != "technical_success":
        raise ValueError("Successful identified Source pool required")
    sources = {}
    for item in pool["sources"]:
        if item["namespace"] != "urbanev-SZH":
            continue
        old = item.get("run", {})
        path = (
            Path(item["path"])
            if "path" in item
            else args.source_pool.parent / old["run_id"] / "final.pt"
        )
        checksum = item.get("checkpoint_sha256", old.get("checkpoint_sha256"))
        if digest(path) != checksum:
            raise ValueError("Source checkpoint changed")
        if item["seed"] in sources:
            raise ValueError("Duplicate Source seed")
        sources[item["seed"]] = (path, checksum)
    if set(sources) != {42, 43, 44}:
        raise ValueError("Exactly three paired Source seeds required")
    args.output.mkdir(parents=True, exist_ok=False)
    base = json.loads(
        (Path(__file__).resolve().parents[1] / "configs/issue21/development-smoke.json").read_text()
    )
    matrix = {
        "scope": cohort["scope"],
        "selection_sha256": args.selection_sha256,
        "source_pool_sha256": args.source_pool_sha256,
        "seeds": cohort["seeds"],
        "days": 90,
        "state_retention": "latest",
        "runs": [],
        "resume_checks": [],
        "status": "running",
    }
    matrix_path = args.output / "matrix.json"

    # A replaceable progress file lives separately; final matrix is create-only.
    def progress() -> None:
        temporary = args.output / "progress.next.json"
        temporary.write_text(json.dumps(matrix, indent=2))
        temporary.replace(args.output / "progress.json")

    try:
        for budget in (7, 14, 28):
            for item in cohort["budgets"][str(budget)]["entities"]:
                entity = item["entity_id"]
                replay = Replay(data[budget], entity, 90)
                replay.prepare_label_index()
                for seed in cohort["seeds"]:
                    for method in cohort["methods"]:
                        config = copy.deepcopy(base)
                        config.update(
                            replay_days=90,
                            development_entities=[entity],
                            method={"name": method},
                            state_retention="latest",
                        )
                        for key in ("initial_training", "online_training", "controller"):
                            config[key]["seed"] = seed
                        output = args.output / f"urbanev-SZH-{entity}-{budget}d-{method}-seed{seed}"
                        result = execute(
                            data[budget],
                            entity,
                            *sources[seed],
                            config,
                            output,
                            device="cuda",
                            prepared_replay=replay,
                        )
                        result["artifact_bytes"] = sum(
                            p.stat().st_size for p in output.rglob("*") if p.is_file()
                        )
                        matrix["runs"].append(result)
                        progress()
                        print(
                            json.dumps(
                                {
                                    k: result[k]
                                    for k in (
                                        "run_id",
                                        "issued_days",
                                        "scored_days",
                                        "active_mae_kwh",
                                        "artifact_bytes",
                                    )
                                }
                            ),
                            flush=True,
                        )
                        if not matrix["resume_checks"] and method == "adaptive":
                            partial = args.output / "resume-prefix"
                            resumed = args.output / "resume-continuation"
                            execute(
                                data[budget],
                                entity,
                                *sources[seed],
                                config,
                                partial,
                                device="cuda",
                                stop_after_ticks=10,
                                prepared_replay=replay,
                            )
                            second = execute(
                                data[budget],
                                entity,
                                *sources[seed],
                                config,
                                resumed,
                                device="cuda",
                                resume_from=partial,
                                prepared_replay=replay,
                            )
                            for key in (
                                "prediction_identity_sha256",
                                "final_branch_state_sha256",
                                "decisions",
                                "candidate_steps",
                                "audit_steps",
                            ):
                                if result[key] != second[key]:
                                    raise ValueError("GPU latest-state resume differs: " + key)
                            for tick in partial.glob("tick-*"):
                                for name in ("forecasts.json", "events.jsonl", "commit.json"):
                                    if (tick / name).read_bytes() != (
                                        resumed / tick.name / name
                                    ).read_bytes():
                                        raise ValueError("Resume rewrote committed history")
                            matrix["resume_checks"].append(
                                {
                                    "run_id": result["run_id"],
                                    "stop_after_ticks": 10,
                                    "result": "exact predictions/decisions/model/optimizer/RNG state hashes and prefix bytes match",
                                }
                            )
        matrix["status"] = "technical_success"
    except Exception as error:
        matrix["status"] = "failed"
        matrix["error"] = repr(error)
        raise
    finally:
        write_json(matrix_path, matrix)
        progress()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("inputs-root", "selection", "source-pool", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    for key in ("selection-sha256", "source-pool-sha256"):
        parser.add_argument("--" + key, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
