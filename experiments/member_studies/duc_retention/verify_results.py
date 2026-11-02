"""Independently check saved study artifacts and summarize station-first metrics."""

import argparse
import json
import math
import statistics
from pathlib import Path

import torch

from .data import sha256


def verify(root: Path) -> dict:
    inventory = json.loads((root / "artifacts.json").read_text())
    for name, record in inventory.items():
        path = root / name
        if path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"Artifact mismatch: {name}")
    source = torch.load(root / "source.pt", weights_only=False, map_location="cpu")
    source_hash = sha256(root / "source.pt")
    results = json.loads((root / "results.json").read_text())
    groups = {}
    for row in results["results"]:
        if row["initialization"] == "blocked_undefined_scale":
            if row["skipped_undefined_scale"] != row["requested_days"]:
                raise ValueError("Blocked coverage not accounted")
            continue
        name = f"target-{row['entity']}-{row['budget']}d-lambda{row['lambda']}"
        state = torch.load(root / f"{name}.pt", weights_only=False, map_location="cpu")
        binding = state["input_binding"]
        if (binding["entity_id"], binding["history_days"], binding["source_checkpoint_sha256"]) != (
            row["entity"],
            row["budget"],
            source_hash,
        ):
            raise ValueError("Checkpoint/result binding mismatch")
        if not torch.equal(state["source_latent_std"], source["source_latent_std"]):
            raise ValueError("Frozen source statistics changed")
        trace = json.loads((root / f"{name}-loss.json").read_text())
        if len(trace) != row["steps"]:
            raise ValueError("Step budget mismatch")
        for step in trace:
            if not math.isclose(
                step["total"],
                step["forecast_mae_scaled"] + row["lambda"] * step["retention"],
                rel_tol=1e-6,
                abs_tol=1e-7,
            ):
                raise ValueError("Saved objective components disagree")
        if row["initialization"] == "source_checkpoint_only":
            if row["steps"] or state["optimizer"]["state"]:
                raise ValueError("Zero-example target received updates")
            if any(
                not torch.equal(value, source["model"][key])
                for key, value in state["model"].items()
            ):
                raise ValueError("Zero-example target changed Source weights")
        if (
            row["requested_days"]
            != row["issued_days"]
            + row["skipped_all_missing_history"]
            + row["skipped_undefined_scale"]
        ):
            raise ValueError("Coverage invariant failed")
        groups.setdefault((row["budget"], row["entity"]), []).append(row)
    for group in groups.values():
        if {row["lambda"] for row in group} != {0.0, 0.01, 0.1}:
            raise ValueError("Missing lambda comparison")
        for field in ("steps", "initial_examples", "issued_days", "scored_days", "unscored_days"):
            if len({row[field] for row in group}) != 1:
                raise ValueError(f"Unpaired lambda comparison: {field}")
    summaries = []
    for budget in (7, 14, 28):
        for weight in (0.0, 0.01, 0.1):
            selected = [
                row
                for row in results["results"]
                if row["budget"] == budget
                and row.get("lambda") == weight
                and row["initialization"] == "target_initial_adaptation"
            ]
            scored = [row for row in selected if row["mae_kwh"] is not None]
            summaries.append(
                {
                    "budget": budget,
                    "lambda": weight,
                    "station_mean_mae_kwh": statistics.mean(row["mae_kwh"] for row in scored),
                    "stations_scored": len(scored),
                    "stations_selected": len(selected),
                    "scored_station_days": sum(row["scored_days"] for row in scored),
                }
            )
    return {
        "verified_artifacts": len(inventory),
        "checkpoints": len(list(root.glob("*.pt"))),
        "source_checkpoint_sha256": source_hash,
        "runtime_seconds": results["seconds"],
        "summaries": summaries,
        "results": results["results"],
        "provenance": json.loads((root / "provenance.json").read_text()),
        "artifact_inventory": inventory,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.run)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(f"Verified {result['verified_artifacts']} artifacts; {result['checkpoints']} checkpoints")


if __name__ == "__main__":
    main()
