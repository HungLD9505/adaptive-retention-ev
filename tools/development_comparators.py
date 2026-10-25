"""GPU core-transfer comparators paired with an identified Development readiness run."""

import argparse
import contextlib
import copy
import json
import os
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

from ev_models.checkpoint import digest, write_json
from ev_runner.replay import Replay
from ev_runner.run import execute, runtime_code
from tools.comparison_matrix import CachedInputs
from tools.development_readiness import validate_cohort

METHODS = ("full_finetuning", "fixed_retention", "online_best")


def reference_cells(cohort: dict, matrix: dict, code_files: dict) -> dict:
    """Require all declared pairs and identical algorithm/config, including null cells."""
    if matrix.get("status") != "technical_success" or matrix.get("seeds") != cohort["seeds"]:
        raise ValueError("Successful reference with the same declared seeds required")
    expected = {
        (int(budget), item["entity_id"], seed, method)
        for budget, group in cohort["budgets"].items()
        for item in group["entities"]
        for seed in cohort["seeds"]
        for method in ("adaptive", "target_only")
    }
    cells = {}
    for row in matrix["runs"]:
        binding = row["binding"]["input"]
        config = row["binding"]["config"]
        seed = config["initial_training"]["seed"]
        key = (binding["history_days"], binding["entity_id"], seed, row["method"]["name"])
        if key not in expected or key in cells:
            raise ValueError("Missing/extra/duplicate reference comparison cell")
        if (
            binding["dataset_id"] != "urbanev"
            or binding["city_id"] != "SZH"
            or row["code"]["files"] != code_files
            or row["code"]["dirty"]
            or config["replay_days"] != 90
            or config["state_retention"] != "latest"
            or config["development_entities"] != [binding["entity_id"]]
            or any(config[k]["seed"] != seed for k in ("online_training", "controller"))
            or binding["input_manifest_sha256"] != cohort["budgets"][str(key[0])]["manifest_sha256"]
        ):
            raise ValueError("Reference algorithm, input or execution profile differs")
        cells[key] = row
    if set(cells) != expected:
        raise ValueError("All reference cells required, including zero-score units")
    result = {}
    for budget, entity, seed, method in expected:
        if method != "adaptive":
            continue
        adaptive, target = (
            cells[budget, entity, seed, method],
            cells[budget, entity, seed, "target_only"],
        )
        configs = [copy.deepcopy(r["binding"]["config"]) for r in (adaptive, target)]
        for config in configs:
            config.pop("method")
        if configs[0] != configs[1]:
            raise ValueError("Reference pairs have different training/controller profiles")
        result[budget, entity, seed] = adaptive
    return result


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise ValueError("Real-data comparison requires Colab CUDA")
    for path, checksum in (
        (args.selection, args.selection_sha256),
        (args.reference_matrix, args.reference_sha256),
        (args.source_pool, args.source_pool_sha256),
    ):
        if digest(path) != checksum:
            raise ValueError("Changed identified cohort/reference/Source pool")
    cohort = json.loads(args.selection.read_text())
    previous = json.loads(args.reference_matrix.read_text())
    if previous["selection_sha256"] != args.selection_sha256:
        raise ValueError("Reference cohort differs")
    data = {
        b: CachedInputs(
            args.inputs_root / f"urbanev-SZH-{b}d", cohort["budgets"][str(b)]["manifest_sha256"]
        )
        for b in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    refs = reference_cells(cohort, previous, runtime_code()["files"])
    pool = json.loads(args.source_pool.read_text())
    if pool["status"] != "technical_success":
        raise ValueError("Successful Source pool required")
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
        if digest(path) != checksum or item["seed"] in sources:
            raise ValueError("Changed/duplicate Source checkpoint")
        sources[item["seed"]] = path, checksum
    if set(sources) != set(cohort["seeds"]):
        raise ValueError("All paired Source seeds required")
    for (_, _, seed), ref in refs.items():
        if ref["source_checkpoint_sha256"] != sources[seed][1]:
            raise ValueError("Reference Source model differs")
    args.output.mkdir(parents=True, exist_ok=False)
    matrix = {
        "scope": "Development core-transfer comparisons; diagnostic settings, no tuning/Final lock",
        "selection_sha256": args.selection_sha256,
        "reference_matrix_sha256": args.reference_sha256,
        "source_pool_sha256": args.source_pool_sha256,
        "seeds": cohort["seeds"],
        "methods": list(METHODS),
        "days": 90,
        "runs": [],
        "status": "running",
    }
    started = time.perf_counter()
    try:
        for budget in (7, 14, 28):
            for item in cohort["budgets"][str(budget)]["entities"]:
                entity = item["entity_id"]
                replay = Replay(data[budget], entity, 90)
                replay.prepare_label_index()
                for seed in cohort["seeds"]:
                    for method in METHODS:
                        config = copy.deepcopy(refs[budget, entity, seed]["binding"]["config"])
                        config["method"] = {"name": method, "fixed_lambda": 0.01}
                        output = args.output / f"urbanev-SZH-{entity}-{budget}d-{method}-seed{seed}"
                        with (
                            (args.output / f"{output.name}.log").open("x") as log,
                            contextlib.redirect_stdout(log),
                            contextlib.redirect_stderr(log),
                        ):
                            result = execute(
                                data[budget],
                                entity,
                                *sources[seed],
                                config,
                                output,
                                device="cuda",
                                prepared_replay=replay,
                            )
                        matrix["runs"].append(result)
                        temporary = args.output / "progress.next.json"
                        temporary.write_text(json.dumps(matrix, indent=2, allow_nan=False))
                        temporary.replace(args.output / "progress.json")
                        print(
                            json.dumps(
                                {
                                    k: result[k]
                                    for k in (
                                        "run_id",
                                        "issued_days",
                                        "scored_days",
                                        "active_mae_kwh",
                                    )
                                }
                            ),
                            flush=True,
                        )
        matrix["status"] = "technical_success"
    except Exception as error:
        matrix.update(status="failed", error=repr(error))
        raise
    finally:
        matrix["wall_seconds"] = time.perf_counter() - started
        write_json(args.output / "matrix.json", matrix)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "selection", "reference-matrix", "source-pool", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("selection-sha256", "reference-sha256", "source-pool-sha256"):
        parser.add_argument("--" + name, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
