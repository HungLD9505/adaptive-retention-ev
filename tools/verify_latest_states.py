"""Read-only CPU content verification of downloaded latest target branch states."""

import argparse
import json
from pathlib import Path

import torch

from ev_evaluation.artifacts import authenticate_matrix
from ev_models.checkpoint import digest, write_json
from ev_runner.state import state_digest


def verify_state(root: Path, report: dict) -> dict:
    """Bind latest serialized bytes to their commit and reported branch contents."""
    ticks = sorted(root.glob("tick-*"))
    if not ticks or len(ticks) != report["ticks"]:
        raise ValueError("Complete tick population required")
    latest = ticks[-1]
    commit = json.loads((latest / "commit.json").read_text())
    if digest(latest / "commit.json") != report["commit_chain"]:
        raise ValueError("Latest commit differs from authenticated run report")
    state_path = latest / "state.pt"
    if digest(state_path) != commit["files"]["state.pt"]:
        raise ValueError("Latest state bytes differ from committed fingerprint")
    state = torch.load(state_path, map_location="cpu", weights_only=True)
    actual = {str(k): state_digest(v) for k, v in state["branches"].items()}
    if actual != report["final_branch_state_sha256"]:
        raise ValueError("Model/optimizer/RNG branch contents differ from run report")
    return {
        "run_id": report["run_id"],
        "latest_state_sha256": digest(state_path),
        "branches": actual,
    }


def verify(matrix_path: Path, proof_path: Path) -> dict:
    """Require complete independent daily verification before checking state tensors."""
    matrix = authenticate_matrix(matrix_path, proof_path)
    results = []
    for row in matrix["runs"]:
        name = row["run_id"]
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Unsafe run identity")
        root = matrix_path.parent / name
        report = json.loads((root / "run.json").read_text())
        if any(row.get(k) != v for k, v in report.items()):
            raise ValueError("Saved report differs from authenticated matrix")
        results.append(verify_state(root, report))
    return {
        "status": "verified",
        "scope": "Downloaded latest target states CPU-loaded and content-rehashed; no training, Source tensor verification or historical-state reconstruction",
        "matrix_sha256": digest(matrix_path),
        "daily_verification_sha256": digest(proof_path),
        "latest_states": len(results),
        "runs": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("matrix", "verification", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new verification output")
    result = verify(args.matrix, args.verification)
    write_json(args.output, result)
    print(json.dumps({k: result[k] for k in ("status", "latest_states")}))


if __name__ == "__main__":
    main()
