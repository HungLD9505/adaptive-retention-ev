"""Run the predeclared #19 matrix on Colab, never on a local CPU by accident."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ev_models.checkpoint import digest, write_json


def run_matrix(inputs_root: Path, output: Path) -> None:
    """One full Source epoch; 2 Development IDs x 3 budgets x 2 fixed lambdas.

    The targets/seed/settings are declared before scores. No online updating or
    controller belongs here. Run each CLI in a fresh process to bound memory.
    """
    output.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    base = json.loads((repo / "configs/issue19/development-smoke.json").read_text())
    source_config = output / "source-config.json"
    write_json(source_config, base)
    commands = []

    def call(stage: str, days: int, config: Path, destination: Path, extra: list[str]) -> dict:
        inputs = inputs_root / f"urbanev-SZH-{days}d"
        args = [
            sys.executable,
            "-m",
            "ev_models.run",
            stage,
            "--inputs",
            str(inputs),
            "--manifest-sha256",
            digest(inputs / "manifest.json"),
            "--config",
            str(config),
            "--output",
            str(destination),
            "--device",
            "cuda",
            *extra,
        ]
        commands.append(args)
        with (output / f"{destination.name}.log").open("x") as stream:
            subprocess.run(args, cwd=repo, stdout=stream, stderr=subprocess.STDOUT, check=True)
        result = json.loads((destination / "run.json").read_text())
        print(
            json.dumps(
                {
                    "run_id": destination.name,
                    "examples": result["training_examples"],
                    "metrics": result["metrics"],
                    "seconds": result["elapsed_seconds"],
                }
            ),
            flush=True,
        )
        return result

    source = output / "source-seed42"
    src = call("source", 7, source_config, source, [])
    results = [src]
    for days in (7, 14, 28):
        for entity in base["development_entities"]:
            for weight in (0, 0.01):
                config = {**base, "training": {**base["training"], "epochs": 3}, "lambda": weight}
                path = output / f"config-{days}-{entity}-{weight}.json"
                write_json(path, config)
                run = output / f"target-{entity}-{days}d-lambda{weight}-seed42"
                extra = [
                    "--source",
                    str(source / "final.pt"),
                    "--source-sha256",
                    src["checkpoint_sha256"],
                    "--entity-id",
                    entity,
                ]
                result = call("target", days, path, run, extra)
                results.append(result)
                if days == 7 and entity == "1001" and weight == 0:
                    resumed = call(
                        "target",
                        days,
                        path,
                        output / "resume-target1001-7d-lambda0",
                        [
                            *extra,
                            "--resume",
                            str(run / "epoch-1.pt"),
                            "--resume-sha256",
                            digest(run / "epoch-1.pt"),
                        ],
                    )
                    if digest(run / "predictions.jsonl") != digest(
                        output / "resume-target1001-7d-lambda0/predictions.jsonl"
                    ):
                        raise ValueError("GPU resume predictions differ")
                    results.append(resumed)
    write_json(
        output / "matrix.json",
        {
            "scope": "Development smoke only; not tuned or final evaluation",
            "commands": commands,
            "runs": results,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_matrix(args.inputs_root.resolve(), args.output.resolve())
