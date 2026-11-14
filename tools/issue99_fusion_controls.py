"""Posthoc equal-weight and loss-free sharing controls on verified saved expert forecasts."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from ev_models.checkpoint import digest


def neutral_weights(cell: dict, initial: float, share: float) -> list[float]:
    """Keep the same initial weight and arrival clock, but remove loss feedback."""
    if (
        not np.isfinite(initial)
        or not 0 <= initial <= 1
        or not np.isfinite(share)
        or not 0 <= share <= 1
    ):
        raise ValueError("Invalid sharing probabilities")
    clocks = [datetime.fromisoformat(o) for o in cell["origins"]]
    arrivals = [datetime.fromisoformat(o) for o in cell["available_at"]]
    if len(arrivals) != len(clocks) or clocks != sorted(set(clocks)):
        raise ValueError("Invalid forecast/availability clock")
    weight = initial
    consumed, result = set(), []
    for i, clock in enumerate(clocks):
        for j in sorted(range(i), key=lambda j: (arrivals[j], clocks[j])):
            if j not in consumed and arrivals[j] <= clock:
                weight = (1 - share) * weight + share * (1 - weight)
                consumed.add(j)
        result.append(weight)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = json.loads((args.run / "summary.json").read_text())
    manifest = {
        r["path"]: r["sha256"]
        for r in json.loads((args.run / "readback-v1/artifact-manifest.json").read_text())
    }
    groups, cells = [], []
    for group in summary["groups"]:
        values = []
        for row in group["cells"]:
            path = (
                args.run
                / f"{group['namespace']}-{group['history_days']}d/cell-{row['target']}-{row['seed']}.json"
            )
            if digest(path) != manifest[str(path)]:
                raise ValueError("Saved cell differs from verified artifact")
            record = json.loads(path.read_text())
            cell = record["cell"]
            metrics = {
                "equal_weight": None,
                "share_only": None,
                "fixed_share": row["mae"]["fixed_share"],
            }
            if cell is not None:
                stable, fast, labels = (np.asarray(cell[k]) for k in ("stable", "fast", "labels"))
                for name, weights in (
                    ("equal_weight", np.full((len(stable), 1), 0.5)),
                    (
                        "share_only",
                        np.asarray(neutral_weights(cell, 0.4307815378871372, 0.1))[:, None],
                    ),
                ):
                    predictions = weights * stable + (1 - weights) * fast
                    metrics[name] = float(np.abs(predictions - labels).mean())
            item = {
                "namespace": group["namespace"],
                "history_days": group["history_days"],
                "target": row["target"],
                "seed": row["seed"],
                **metrics,
            }
            cells.append(item)
            values.append(item)
        means = {}
        for method in ("equal_weight", "share_only", "fixed_share"):
            stations = []
            for target in group["station_means"]:
                scores = [
                    r[method] for r in values if r["target"] == target and r[method] is not None
                ]
                if scores:
                    stations.append(float(np.mean(scores)))
            means[method] = float(np.mean(stations))
        np.testing.assert_allclose(
            means["fixed_share"], group["macro_mae"]["fixed_share"], atol=1e-12, rtol=0
        )
        groups.append(
            {"namespace": group["namespace"], "history_days": group["history_days"], **means}
        )
    for name, rows in (("groups", groups), ("cells", cells)):
        with (args.output / f"{name}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    result = {
        "scope": "Posthoc diagnostic controls; no parameter selection or new training",
        "verified_cell_count": len(cells),
        "groups": groups,
        "initial_weight": 0.4307815378871372,
        "share": 0.1,
        "adaptive_below_control": {
            m: sum(g["fixed_share"] < g[m] for g in groups) for m in ("equal_weight", "share_only")
        },
        "percent_reduction_ranges": {
            m: [
                min(100 * (g[m] - g["fixed_share"]) / g[m] for g in groups),
                max(100 * (g[m] - g["fixed_share"]) / g[m] for g in groups),
            ]
            for m in ("equal_weight", "share_only")
        },
        "source_summary_sha256": digest(args.run / "summary.json"),
        "script_sha256": digest(Path(__file__)),
    }
    (args.output / "summary.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "groups"}, indent=2))


if __name__ == "__main__":
    main()
