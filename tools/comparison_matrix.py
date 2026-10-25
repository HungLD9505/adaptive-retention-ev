"""Predeclared GPU Development comparison matrix; datasets/cities never share Source weights."""

import argparse
import contextlib
import copy
import json
import os
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

from ev_baselines.policies import METHODS, Method, ablation_aliases
from ev_control.confidence import ControllerConfig
from ev_models.checkpoint import digest, write_json
from ev_models.data import InputRun
from ev_runner.replay import Replay
from ev_runner.run import execute


class CachedInputs(InputRun):
    """Reuse immutable, already-validated target-prefix records within one process."""

    def training(self, role: str, entity_id: str | None = None) -> list[dict]:
        if not hasattr(self, "_training_cache"):
            self._training_cache = {}
        key = (role, entity_id)
        if key not in self._training_cache:
            self._training_cache[key] = super().training(role, entity_id)
        return self._training_cache[key]


def execute_matrix(
    inputs_root: Path,
    output: Path,
    namespaces: list[str],
    *,
    reused_source: Path | None = None,
    reused_source_sha: str | None = None,
    seeds: tuple[int, ...] = (42,),
    days: int = 43,
) -> dict:
    if not torch.cuda.is_available():
        raise ValueError("Comparison training requires a Colab CUDA runtime")
    output.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    base = json.loads((repo / "configs/issue21/development-smoke.json").read_text())
    matrix = {
        "scope": "Development technical comparison smoke; not a configuration lock or Final evaluation",
        "seeds": list(seeds),
        "replay_days": days,
        "namespaces": namespaces,
        "sources": [],
        "runs": [],
        "failures": [],
        "aliases": ablation_aliases(ControllerConfig(**base["controller"]), 0.01),
    }
    started = time.perf_counter()
    try:
        for namespace in namespaces:
            paths = {budget: inputs_root / f"{namespace}-{budget}d" for budget in (7, 14, 28)}
            inputs = {
                budget: CachedInputs(path, digest(path / "manifest.json"))
                for budget, path in paths.items()
            }
            if len({x.source_hash for x in inputs.values()}) != 1:
                raise ValueError("Budget variants must identify the same Source population")
            # Choose by role and allowed-prefix readiness only, never future activity/error.
            candidates = set.intersection(
                *[
                    {
                        key[-1]
                        for key, row in x.entities.items()
                        if row["role"] == "development"
                        and row["status"] == "ready"
                        and row["initial_trainable"] > 0
                    }
                    for x in inputs.values()
                ]
            )
            if not candidates:
                raise ValueError("No common prefix-ready Development target across budgets")
            entity = min(candidates)
            print(
                json.dumps(
                    {
                        "namespace": namespace,
                        "target": entity,
                        "selection": "lexicographically first common prefix-ready Development ID; no future-value filtering",
                    }
                ),
                flush=True,
            )
            sources = {}
            # Three source seeds support the explicitly declared uncertainty ensemble.
            for seed in sorted(set(seeds) | {42, 43, 44}):
                if namespace == "urbanev-SZH" and seed == 42 and reused_source:
                    if not reused_source_sha or digest(reused_source) != reused_source_sha:
                        raise ValueError("Reused Source fingerprint mismatch")
                    sources[seed] = (reused_source, reused_source_sha)
                    matrix["sources"].append(
                        {
                            "namespace": namespace,
                            "seed": seed,
                            "reused": True,
                            "checkpoint_sha256": reused_source_sha,
                            "path": str(reused_source),
                        }
                    )
                    continue
                config = {
                    "training": {**base["initial_training"], "seed": seed, "epochs": 1},
                    "lambda": 0,
                    "development_entities": [entity],
                    "evaluation_origins": days,
                }
                config_path = output / f"{namespace}-source{seed}.json"
                write_json(config_path, config)
                destination = output / f"{namespace}-source{seed}"
                command = [
                    sys.executable,
                    "-m",
                    "ev_models.run",
                    "source",
                    "--inputs",
                    str(paths[7]),
                    "--manifest-sha256",
                    inputs[7].sha256,
                    "--config",
                    str(config_path),
                    "--output",
                    str(destination),
                    "--device",
                    "cuda",
                ]
                before = time.perf_counter()
                with (output / f"{destination.name}.log").open("x") as stream:
                    subprocess.run(
                        command, cwd=repo, stdout=stream, stderr=subprocess.STDOUT, check=True
                    )
                report = json.loads((destination / "run.json").read_text())
                sources[seed] = (destination / "final.pt", report["checkpoint_sha256"])
                matrix["sources"].append(
                    {
                        "namespace": namespace,
                        "seed": seed,
                        "reused": False,
                        "subprocess_wall_seconds": time.perf_counter() - before,
                        "command": command,
                        "run": report,
                    }
                )
                print(
                    json.dumps(
                        {
                            "source": destination.name,
                            "examples": report["training_examples"],
                            "wall_seconds": matrix["sources"][-1]["subprocess_wall_seconds"],
                        }
                    ),
                    flush=True,
                )
            ensemble = tuple(sources[k] for k in (42, 43, 44))
            for budget in (7, 14, 28):
                before = time.perf_counter()
                replay = Replay(inputs[budget], entity, days)
                preparation_seconds = time.perf_counter() - before
                for seed in seeds:
                    for name in METHODS:
                        if (
                            name == "without_confidence"
                            and matrix["aliases"]["without_confidence"] != "without_confidence"
                        ):
                            continue
                        config = copy.deepcopy(base)
                        config["replay_days"] = days
                        config["development_entities"] = [entity]
                        for key in ("initial_training", "online_training", "controller"):
                            config[key]["seed"] = seed
                        if name in {"block7", "block28"}:
                            config["controller"]["block_days"] = 7 if name == "block7" else 28
                        method = Method(
                            name,
                            proxy_thresholds=(0.01, 0.05)
                            if name == "uncertainty"
                            else (0.5, 1.5)
                            if name == "drift"
                            else (0.1, 0.5),
                        )
                        config["method"] = asdict(method)
                        destination = output / f"{namespace}-{entity}-{budget}d-{name}-seed{seed}"
                        torch.cuda.reset_peak_memory_stats()
                        before = time.perf_counter()
                        with (
                            (output / f"{destination.name}.log").open("x") as log,
                            contextlib.redirect_stdout(log),
                            contextlib.redirect_stderr(log),
                        ):
                            result = execute(
                                inputs[budget],
                                entity,
                                *sources[seed],
                                config,
                                destination,
                                device="cuda",
                                ensemble_sources=ensemble if name == "uncertainty" else (),
                                prepared_replay=replay,
                            )
                        result["matrix_cell_wall_seconds"] = time.perf_counter() - before
                        result["shared_replay_preparation_seconds"] = preparation_seconds
                        matrix["runs"].append(result)
                        print(
                            json.dumps(
                                {
                                    k: result[k]
                                    for k in (
                                        "run_id",
                                        "issued_days",
                                        "scored_days",
                                        "candidate_steps",
                                        "active_mae_kwh",
                                        "matrix_cell_wall_seconds",
                                    )
                                }
                            ),
                            flush=True,
                        )
        matrix["status"] = "technical_success"
    except Exception as error:
        matrix["status"] = "failed"
        matrix["failures"].append(
            {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            }
        )
        raise
    finally:
        matrix["matrix_wall_seconds"] = time.perf_counter() - started
        write_json(output / "matrix.json", matrix)
    return matrix


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--namespaces", nargs="+", required=True)
    parser.add_argument("--reused-source", type=Path)
    parser.add_argument("--reused-source-sha256")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42])
    parser.add_argument("--days", type=int, default=43)
    args = parser.parse_args()
    execute_matrix(
        args.inputs_root.resolve(),
        args.output.resolve(),
        args.namespaces,
        reused_source=args.reused_source,
        reused_source_sha=args.reused_source_sha256,
        seeds=tuple(args.seeds),
        days=args.days,
    )


if __name__ == "__main__":
    main()
