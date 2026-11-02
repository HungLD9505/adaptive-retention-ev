"""Create-only study entry point; this refactor has no new real-data training evidence."""

import argparse
import json
import logging
import math
import platform
import subprocess
from pathlib import Path

import numpy as np
import torch

from .study_data import load_development_stream, load_source_training_samples, open_inputs
from .study_runner import pretrain_source_model, run_target_replay_study, sha256_file


def _json_values(value: object) -> object:
    """Represent undefined diagnostic bounds as JSON null, not nonstandard Infinity."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_values(v) for v in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-root", type=Path, required=True)
    parser.add_argument(
        "--manifest-pins", type=Path, required=True, help="JSON: budget string to SHA-256"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--entity-id", nargs=3, required=True)
    parser.add_argument("--history-budgets", nargs="+", type=int, default=[7, 14, 28])
    parser.add_argument("--source-samples", type=int, default=300)
    parser.add_argument("--source-epochs", type=int, default=5)
    parser.add_argument("--days", type=int, default=56)
    parser.add_argument("--block-size", type=int, default=14)
    parser.add_argument("--b-min", type=int, default=10)
    parser.add_argument("--delta", type=float, default=0.0)
    parser.add_argument("--lambda-low", type=float, default=0.1)
    parser.add_argument("--lambda-high", type=float, default=1.0)
    parser.add_argument("--initial-lambda", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    if args.block_size < 1 or args.days < 1 or args.days % args.block_size:
        raise ValueError("Choose positive complete calendar blocks")
    if args.source_epochs < 1 or args.source_samples < 1:
        raise ValueError("Source epochs/sample limit must be positive")
    if len(set(args.history_budgets)) != len(args.history_budgets):
        raise ValueError("Duplicate history budgets")
    pins = json.loads(args.manifest_pins.read_text())
    budgets = set(args.history_budgets) | {14}
    inputs = {
        b: open_inputs(
            args.inputs_root / f"{args.entity_id[0]}-{args.entity_id[1]}-{b}d", pins[str(b)]
        )
        for b in budgets
    }
    if any(inp.config["history_days"] != b for b, inp in inputs.items()):
        raise ValueError("Input budget differs from its declared manifest pin")
    if len({inp.source_hash for inp in inputs.values()}) != 1:
        raise ValueError("Source identity differs across history budgets")
    replays = {
        b: load_development_stream(inputs[b], args.entity_id, args.days)
        for b in args.history_budgets
    }
    if any(r.delay.total_seconds() != 0 for r in replays.values()):
        raise ValueError("Use the primary runner for nonzero configured label delays")
    # Validate every target prefix before any training or create-only output begins.
    for b in args.history_budgets:
        inputs[b].training("development", args.entity_id[2])
    x, c, y = load_source_training_samples(inputs[14], args.source_samples)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    source, scale = pretrain_source_model(
        x, c, y, epochs=args.source_epochs, device=device, seed=args.seed
    )
    torch.save(source.state_dict(), args.output_dir / "source.pt")
    torch.save(scale, args.output_dir / "latent-scale.pt")
    results = {}
    for b, replay in replays.items():
        results[str(b)] = run_target_replay_study(
            source,
            scale,
            replay,
            b,
            args.entity_id,
            forecast_path=args.output_dir / f"forecasts-{b}d.jsonl",
            block_size=args.block_size,
            lambda_low=args.lambda_low,
            lambda_high=args.lambda_high,
            initial_lambda=args.initial_lambda,
            b_min=args.b_min,
            delta=args.delta,
            seed=args.seed,
            device=device,
        )
    code = (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[3]
        )
        .decode()
        .strip()
    )
    payload = {
        "schema": "cyber-study-guarded-io-v2",
        "config": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "code_commit": code,
        "tracked_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=Path(__file__).resolve().parents[3],
            ).strip()
        ),
        "study_source_sha256": {
            p.name: sha256_file(p) for p in sorted(Path(__file__).parent.glob("*.py"))
        },
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "device": str(device),
        },
        "manifest_pins": pins,
        "source_sha256": sha256_file(args.output_dir / "source.pt"),
        "results": results,
    }
    with (args.output_dir / "results.json").open("x", encoding="utf-8") as handle:
        json.dump(_json_values(payload), handle, indent=2, allow_nan=False)
