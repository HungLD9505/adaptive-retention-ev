"""One prespecified controller attempt on old, exposed Development expert vectors."""

import argparse
import json
from pathlib import Path

import numpy as np

from ev_control.expert_mix import fit_static_weight, forecast_mixture
from ev_control.weighting_followup import METHODS, replay_weighting
from ev_models.checkpoint import digest
from tools.fusion_evidence import write_csv


def evaluate(protocol_path: Path, output: Path) -> dict:
    """Freeze candidate selection before considering any newer evaluation cohort."""
    protocol = json.loads(protocol_path.read_text())
    for name, expected in protocol["code_sha256"].items():
        if digest(Path(name)) != expected:
            raise ValueError("Candidate code changed after registration")
    path = Path(protocol["development_cells"]["path"])
    if digest(path) != protocol["development_cells"]["sha256"]:
        raise ValueError("Previously exposed Development vectors changed")
    output.mkdir(parents=True, exist_ok=False)
    rows = json.loads(path.read_text())
    expected = {(t, s) for t in protocol["development_ids"] for s in [42, 43, 44]}
    if {(r["target"], r["seed"]) for r in rows} != expected or len(rows) != len(expected):
        raise ValueError("Development matrix differs from registration")
    records, cell_results, diagnostic = [], [], []
    for row in rows:
        cell = row["cell"]
        arms = {name: replay_weighting(cell, name, protocol["initial_weight"]) for name in METHODS}
        arms.update(
            {
                name: forecast_mixture(cell, w)
                for name, w in [
                    ("fixed", 1.0),
                    ("fast", 0.0),
                    ("static", protocol["initial_weight"]),
                    ("equal", 0.5),
                ]
            }
        )
        arms["legacy"] = forecast_mixture(cell, protocol["initial_weight"], eta=0.1, share=0.1)
        arms["loss_free_share"] = dict(arms["legacy"])
        weight, loss_free = protocol["initial_weight"], []
        for index in range(len(cell["origins"])):
            # Legacy events already authenticate which feedback precedes each origin.
            n = sum(e["at"] == cell["origins"][index] for e in arms["legacy"]["events"])
            for _ in range(n):
                weight = 0.1 + 0.8 * weight
            loss_free.append(weight)
        stable, fast, labels = (np.asarray(cell[k]) for k in ("stable", "fast", "labels"))
        loss_free_predictions = (
            np.asarray(loss_free)[:, None] * stable + (1 - np.asarray(loss_free)[:, None]) * fast
        )
        arms["loss_free_share"] = {"mae": float(abs(loss_free_predictions - labels).mean())}
        for name, arm in arms.items():
            records.append(
                dict(target=row["target"], seed=row["seed"], method=name, mae=arm["mae"])
            )
        hindsight = fit_static_weight([cell])
        oracle = float(np.minimum(abs(stable - labels).mean(1), abs(fast - labels).mean(1)).mean())
        diagnostic.append(
            dict(
                target=row["target"],
                seed=row["seed"],
                daily_expert_oracle=oracle,
                hindsight_static_weight=hindsight,
                hindsight_static_mae=forecast_mixture(cell, hindsight)["mae"],
            )
        )
        cell_results.append(dict(target=row["target"], seed=row["seed"], cell=cell, arms=arms))
    methods = sorted({r["method"] for r in records})
    means = {
        m: float(
            np.mean(
                [
                    np.mean([r["mae"] for r in records if r["target"] == t and r["method"] == m])
                    for t in protocol["development_ids"]
                ]
            )
        )
        for m in methods
    }
    selected = min(METHODS, key=lambda m: (means[m], METHODS.index(m)))
    proceed = all(means[selected] < means[ref] for ref in ["fixed", "static", "legacy"])
    result = dict(
        schema="bounded-weighting-development-v1",
        protocol_sha256=digest(protocol_path),
        means=means,
        selected=selected,
        proceed_to_new_cohort=proceed,
        reason="Proceed only if selected candidate has lower equal-entity/seed MAE than Fixed, static and legacy; otherwise stop without new cohort execution.",
        oracle_scope="Hindsight diagnostics only; unavailable for deployment or selection",
        cells=36,
    )
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "cells.json").write_text(json.dumps(cell_results, allow_nan=False) + "\n")
    write_csv(output / "development-mae.csv", records)
    write_csv(output / "hindsight-diagnostics.csv", diagnostic)
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    evaluate(a.protocol, a.output)


if __name__ == "__main__":
    main()
