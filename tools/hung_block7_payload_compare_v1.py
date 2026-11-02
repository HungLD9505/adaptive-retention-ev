"""Compare byte-pinned historical Block7 and Main checkpoint payloads, without training."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

from tools.hung_block7_historical_import import ROOT, load_pairs, request_rows, verify_stage
from tools.hung_e2e_gate import equal_state

STAGE = ROOT / ".cache/block7-historical-import-v1"
MAIN_BASE = ROOT / ".cache/kaggle-payload-v2/payload/.cache/provider/checkpoints"
OUTPUT = ROOT / "docs/reports/evidence/hung-block7-payload-comparison-20261029-v1.json"
REQUIRED_SOURCE = {
    "architecture",
    "seed",
    "training_step",
    "model_state",
    "optimizer_type",
    "optimizer_state",
    "latent_scale",
    "rng_state",
    "input_binding",
    "schema",
    "code_sha",
}
REQUIRED_TARGET = REQUIRED_SOURCE | {
    "initial_model_sha256",
    "initial_retention_kind",
    "initial_retention_weight",
    "initialization_kind",
}


def sha_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_checkpoint(path: Path, expected_sha: str, root: Path) -> dict:
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Checkpoint path escapes its repository staging root")
    if not path.is_file() or sha_file(path) != expected_sha:
        raise ValueError(f"Missing or changed checkpoint: {expected_sha}")
    value = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(value, dict):
        raise ValueError("Checkpoint payload must be a dictionary")
    return value


def compare_payload(old: dict, main: dict, role: str, old_source: str, main_source: str) -> dict:
    required = REQUIRED_SOURCE if role == "source" else REQUIRED_TARGET
    if role not in {"source", "target"} or set(old) != set(main) or set(old) != required:
        raise ValueError(f"Unexpected {role} checkpoint payload keys")
    differing = sorted(key for key in old if not equal_state(old[key], main[key]))
    expected = ["code_sha"] if role == "source" else ["code_sha", "input_binding"]
    if differing != expected:
        raise ValueError(
            f"{role} payload differs outside permitted provenance metadata: {differing}"
        )
    if role == "target":
        left, right = old["input_binding"], main["input_binding"]
        if not isinstance(left, dict) or not isinstance(right, dict) or set(left) != set(right):
            raise ValueError("Target input binding shape differs")
        binding_diff = sorted(key for key in left if not equal_state(left[key], right[key]))
        if binding_diff != ["source_checkpoint_sha256"]:
            raise ValueError(f"Unexpected Target input binding difference: {binding_diff}")
        if (
            left["source_checkpoint_sha256"] != old_source
            or right["source_checkpoint_sha256"] != main_source
        ):
            raise ValueError("Target input binding does not match pinned Source files")
    else:
        binding_diff = []
    return {
        "role": role,
        "state_fields_equal": True,
        "different_top_level_fields": differing,
        "different_input_binding_fields": binding_diff,
    }


def compare_all(stage: Path = STAGE, main_base: Path = MAIN_BASE) -> dict:
    if not stage.resolve().is_relative_to(ROOT.resolve()) or not main_base.resolve().is_relative_to(
        ROOT.resolve()
    ):
        raise ValueError("Comparison paths must remain inside the current repository")
    pairs = load_pairs()
    staged = verify_stage(request_rows(pairs), stage)
    if not staged["complete"]:
        raise ValueError(f"Historical checkpoint byte gate incomplete: {staged['counts']}")
    source_pairs = {}
    for row in pairs:
        key = (row["budget_days"], row["seed"])
        pair = (row["historical_source_sha256"], row["main_source_sha256"])
        if key in source_pairs and source_pairs[key] != pair:
            raise ValueError("Source hashes disagree within one budget/seed stratum")
        source_pairs[key] = pair
    if len(source_pairs) != 9:
        raise ValueError("Expected nine unique Source budget/seed strata")
    result = []
    for role, rows in (
        (
            "source",
            [
                {
                    "historical_source_sha256": old_sha,
                    "main_source_sha256": main_sha,
                    "budget_days": budget,
                    "seed": seed,
                    "historical_run_id": None,
                }
                for (budget, seed), (old_sha, main_sha) in sorted(source_pairs.items())
            ],
        ),
        ("target", pairs),
    ):
        for row in rows:
            old_sha = row[f"historical_{role}_sha256"]
            main_sha = row[f"main_{role}_sha256"]
            old_path = stage / f"{old_sha}.pt"
            main_path = main_base / main_sha / role / f"{role}_checkpoint.pt"
            old = checked_checkpoint(old_path, old_sha, stage)
            main = checked_checkpoint(main_path, main_sha, main_base)
            comparison = compare_payload(
                old,
                main,
                role,
                row["historical_source_sha256"] if role == "target" else old_sha,
                row["main_source_sha256"] if role == "target" else main_sha,
            )
            result.append(
                {
                    "budget_days": int(row["budget_days"]),
                    "seed": int(row["seed"]),
                    "historical_run_id": row["historical_run_id"],
                    "historical_checkpoint_sha256": old_sha,
                    "main_checkpoint_sha256": main_sha,
                    **comparison,
                }
            )
    if len(result) != 78 or sum(row["role"] == "source" for row in result) != 9:
        raise ValueError("Comparison did not cover exact 9 Source and 69 Target pairs")
    return {
        "schema": "hung-block7-payload-comparison-v1",
        "scope": "byte-pinned checkpoint state equality; not origin-level or peer acceptance",
        "pair_table_sha256": sha_file(
            ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
        ),
        "source_pairs_equal": 9,
        "target_pairs_equal": 69,
        "comparisons": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Output must remain inside the current repository")
    result = compare_all()
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.output.exists():
        if args.output.read_bytes() != payload:
            raise ValueError("Existing comparison evidence differs; outputs are create-only")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(payload)
    print(
        json.dumps(
            {
                "source_pairs_equal": 9,
                "target_pairs_equal": 69,
                "output_sha256": hashlib.sha256(payload).hexdigest(),
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
