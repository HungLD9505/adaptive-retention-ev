"""Run the predeclared #39 Development cases with create-only outputs.

This runner uses the existing versioned source/target/replay CLI. It never
chooses an entity from outcomes, and it does not select model hyperparameters.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.cli import _code_identity, _examples, _load_run
from experiments.hung_sprint2.selection import select_development


def _verified_output(path: Path, checkpoint_name: str, executed_sources: dict) -> dict | None:
    if not path.exists():
        return None
    manifest = path / "run_manifest.json"
    checkpoint = path / checkpoint_name
    if not manifest.is_file() or not checkpoint.is_file():
        raise ValueError(f"Incomplete existing run; preserve and inspect it: {path}")
    record = json.loads(manifest.read_text(encoding="utf-8"))
    expected = record.get("checkpoint_sha256", record.get("final_runner_checkpoint_sha256"))
    if (
        record.get("status") != "completed"
        or record.get("run_id") != path.name
        or record.get("code", {}).get("executed_sources") != executed_sources
        or expected != sha256_file(checkpoint)
    ):
        raise ValueError(f"Existing run has different code or checkpoint hash: {path}")
    return record


def _invoke(arguments: list[str], *, execute: bool) -> None:
    print(" ".join(arguments), flush=True)
    if execute:
        subprocess.run(
            [sys.executable, "-m", "experiments.hung_sprint2.cli", *arguments], check=True
        )


def verification_split_limit(block_days: int, max_origins: int) -> int:
    """Keep a resumed segment after two block boundaries, including the next origin."""
    if (
        isinstance(block_days, bool)
        or not isinstance(block_days, int)
        or block_days < 1
        or isinstance(max_origins, bool)
        or not isinstance(max_origins, int)
        or max_origins < 2 * block_days + 1
    ):
        raise ValueError("Verification replay needs two block boundaries and a next origin")
    return min(3 * block_days, max_origins - 1)


def run(args: argparse.Namespace) -> None:
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("schema") != "hung-sprint2-development-config-v1":
        raise ValueError("Expected reviewed Development config v1")
    target_kind = config["target"].get("retention_kind", "latent")
    replay_kind = config["replay"].get("retention_kind", "latent")
    if target_kind != replay_kind or target_kind not in {"latent", "parameter"}:
        raise ValueError("Target/replay retention kind differs")
    if target_kind == "parameter" and (
        config["target"]["retention_weight"] != config["replay"]["initial_level"]
    ):
        raise ValueError("Parameter ablation initial lambda differs from target initialization")
    target_initialization = config["target"].get("initialization_kind", "source")
    replay_initialization = config["replay"].get("initialization_kind", "source")
    if target_initialization != replay_initialization or target_initialization not in {
        "source",
        "random_target",
    }:
        raise ValueError("Target/replay initialization kind differs")
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    runs = []
    for budget in (7, 14, 28):
        path = args.input_base / f"urbanev-SZH-{budget}d"
        runs.append((path, sha256_file(path / "manifest.json")))
    if selection != select_development(runs):
        raise ValueError("Selection artifact differs from verified Development metadata")
    if args.device == "cuda":
        import torch

        if not torch.cuda.is_available():
            raise ValueError("CUDA was requested but is unavailable")
    code_identity = _code_identity()
    code = code_identity["executed_sources"]
    if args.execute:
        args.output_root.mkdir(parents=True, exist_ok=True)
        identity = {
            "schema": "hung-sprint2-development-matrix-v1",
            "code": code_identity,
            "selection_sha256": sha256_file(args.selection),
            "config_sha256": sha256_file(args.config),
            "input_manifest_sha256": {
                str(n): digest for n, (_, digest) in zip((7, 14, 28), runs, strict=True)
            },
            "phase": args.phase,
            "device": args.device,
            "budgets": sorted(set(args.budgets)),
            "seeds": sorted(set(args.seeds)),
        }
        marker = args.output_root / "matrix_identity.json"
        if marker.exists():
            if json.loads(marker.read_text(encoding="utf-8")) != identity:
                raise ValueError("Existing matrix identity differs; use a new output root")
        else:
            with marker.open("x", encoding="utf-8") as stream:
                json.dump(identity, stream, indent=2, sort_keys=True)
                stream.write("\n")
    for budget, (input_run, manifest_sha) in zip((7, 14, 28), runs, strict=True):
        if budget not in args.budgets:
            continue
        manifest = _load_run(input_run, manifest_sha)
        source_rows, source_available = _examples(input_run, manifest, "source", limit=1)
        if not source_rows or source_available < 2:
            raise ValueError("Source training population is too small")
        selected = selection["budgets"][str(budget)]
        entities = (
            selected["verification_entity_ids"]
            if args.phase == "verification"
            else [row["entity_id"] for row in selected["representative_entities"]]
        )
        selected_by_id = {row["entity_id"]: row for row in selected["representative_entities"]}
        for seed in config["seeds"]:
            if seed not in args.seeds:
                continue
            base = args.output_root / f"{budget}d" / f"seed-{seed}"
            source_output = base / "source"
            source_args = [
                "source-smoke",
                "--input-run",
                str(input_run),
                "--manifest-sha256",
                manifest_sha,
                "--output",
                str(source_output),
                "--steps",
                str(math.ceil(source_available / config["source"]["batch_size"])),
                "--batch-size",
                str(config["source"]["batch_size"]),
                "--learning-rate",
                str(config["source"]["learning_rate"]),
                "--calendar-hidden",
                str(config["source"]["calendar_hidden"]),
                "--seed",
                str(seed),
                "--device",
                args.device,
            ]
            if args.execute:
                base.mkdir(parents=True, exist_ok=True)
            prior = _verified_output(source_output, "source_checkpoint.pt", code)
            if prior is None:
                _invoke(source_args, execute=args.execute)
            source_checkpoint = source_output / "source_checkpoint.pt"
            for entity_id in entities:
                if entity_id not in selected_by_id:
                    raise ValueError("Verification entity is absent from representative selection")
                target_info = selected_by_id[entity_id]
                target_output = base / f"entity-{entity_id}" / "target"
                target_args = [
                    "target-smoke",
                    "--input-run",
                    str(input_run),
                    "--manifest-sha256",
                    manifest_sha,
                    "--source-input-run",
                    str(input_run),
                    "--source-manifest-sha256",
                    manifest_sha,
                    "--source-checkpoint",
                    str(source_checkpoint),
                    "--entity-id",
                    entity_id,
                    "--output",
                    str(target_output),
                    "--steps",
                    str(
                        max(
                            1,
                            math.ceil(
                                target_info["initial_trainable"] / config["target"]["batch_size"]
                            ),
                        )
                    ),
                    "--batch-size",
                    str(config["target"]["batch_size"]),
                    "--learning-rate",
                    str(config["target"]["learning_rate"]),
                    "--retention-weight",
                    str(config["target"]["retention_weight"]),
                    "--retention-kind",
                    target_kind,
                    "--initialization-kind",
                    target_initialization,
                    "--epsilon",
                    str(config["target"]["epsilon"]),
                    "--seed",
                    str(seed),
                    "--device",
                    args.device,
                ]
                if args.execute:
                    target_output.parent.mkdir(parents=True, exist_ok=True)
                prior = _verified_output(target_output, "target_checkpoint.pt", code)
                if prior is None:
                    _invoke(target_args, execute=args.execute)
                replay_parent = base / f"entity-{entity_id}"
                replay_config = config["replay"]
                replay_args = [
                    "replay-development",
                    "--input-run",
                    str(input_run),
                    "--manifest-sha256",
                    manifest_sha,
                    "--source-input-run",
                    str(input_run),
                    "--source-manifest-sha256",
                    manifest_sha,
                    "--source-checkpoint",
                    str(source_checkpoint),
                    "--target-checkpoint",
                    str(target_output / "target_checkpoint.pt"),
                    "--entity-id",
                    entity_id,
                    "--seed",
                    str(seed),
                    "--device",
                    args.device,
                    "--epsilon",
                    str(config["target"]["epsilon"]),
                    *[
                        item
                        for key, value in replay_config.items()
                        if key not in {"missing_day_bootstrap_policy", "max_origins"}
                        for item in ("--" + key.replace("_", "-"), str(value))
                    ],
                ]
                first_limit = verification_split_limit(
                    replay_config["block_days"], replay_config["max_origins"]
                )
                first_output = replay_parent / f"replay-{first_limit}"
                first = _verified_output(first_output, "runner_checkpoint.pt", code)
                if first is None:
                    _invoke(
                        [
                            *replay_args,
                            "--max-origins",
                            str(first_limit),
                            "--output",
                            str(first_output),
                        ],
                        execute=args.execute,
                    )
                final_limit = replay_config["max_origins"]
                if final_limit > first_limit:
                    final_output = replay_parent / f"replay-{final_limit}"
                    final = _verified_output(final_output, "runner_checkpoint.pt", code)
                    if final is None:
                        _invoke(
                            [
                                *replay_args,
                                "--max-origins",
                                str(final_limit),
                                "--resume-checkpoint",
                                str(first_output / "runner_checkpoint.pt"),
                                "--output",
                                str(final_output),
                            ],
                            execute=args.execute,
                        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-base", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("verification", "representative"), required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--budgets", nargs="+", type=int, choices=(7, 14, 28), default=[7, 14, 28])
    parser.add_argument("--seeds", nargs="+", type=int, choices=(7, 11, 19), default=[7, 11, 19])
    parser.add_argument("--execute", action="store_true")
    run(parser.parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
