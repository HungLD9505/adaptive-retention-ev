"""Authenticate complete Development matrices against independent verifier output."""

import json
import math
from pathlib import Path

from ev_models.checkpoint import digest


def authenticate_matrix(path: Path, verification: Path) -> dict:
    """Require every verifier cell, score and chain, not a successful-status label."""
    matrix, proof = (json.loads(p.read_text()) for p in (path, verification))
    if (
        matrix.get("status") != "technical_success"
        or proof.get("status") != "verified"
        or proof.get("matrix_sha256") != digest(path)
    ):
        raise ValueError("Matrix must match independent verification fingerprint")
    checked = {r["run_id"]: r for r in proof["runs"]}
    if (
        len(checked) != len(proof["runs"])
        or len(matrix["runs"]) != len(checked)
        or set(checked) != {r["run_id"] for r in matrix["runs"]}
    ):
        raise ValueError("Verifier population differs from matrix")
    for row in matrix["runs"]:
        v = checked[row["run_id"]]
        for name, field in (
            ("issued_days", "issued"),
            ("scored_days", "scored"),
            ("commit_chain", "commit_chain"),
        ):
            if row[name] != v[field]:
                raise ValueError("Verifier identity/count/chain differs")
        for name, field in (("active_mae_kwh", "mae_kwh"), ("active_rmse_kwh", "rmse_kwh")):
            a, b = row[name], v[field]
            if a is None or b is None:
                if a is not b:
                    raise ValueError("Verifier null score differs")
            elif not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-10):
                raise ValueError("Verifier score differs")
        for name in ("issued_origins_sha256", "scored_origins_sha256"):
            if name in v:
                if name in row and row[name] != v[name]:
                    raise ValueError("Verifier origin population differs")
                # Enrich only this in-memory copy. The immutable matrix bytes and
                # its proof fingerprint remain unchanged for historical runs.
                row[name] = v[name]
    return matrix
