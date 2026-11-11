"""Render source-bound scientific figures and equation images for the review manuscript."""

import argparse
import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ev_models.checkpoint import digest

NAMESPACES = [
    "urbanev-SZH",
    "charged-AMS",
    "charged-JHB",
    "charged-LOA",
    "charged-MEL",
    "charged-SPO",
    "charged-SZH",
]
ROOT = Path(__file__).resolve().parents[1]


def finish(fig: plt.Figure, path: Path) -> None:
    for suffix in ("png", "pdf"):
        fig.savefig(path.with_suffix("." + suffix), dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--full-run", type=Path, required=True)
    args = parser.parse_args()
    out = args.output / "figures"
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "pdf.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    for name in ("epoch-selection", "history-comparison"):
        for suffix in ("png", "pdf"):
            shutil.copyfile(
                ROOT / f"report/teacher-review-20261110/figures/{name}.{suffix}",
                out / f"{name}.{suffix}",
            )
    baseline = ROOT / "docs/reports/issue99-teacher-review-20261111"
    figures = []
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    for ax, author in zip(axes, ("cyber", "duc"), strict=True):
        rows = list(csv.DictReader((baseline / f"{author}-summary.csv").open()))
        lookup = {(r["model"].lower(), r["mode"]): float(r["mae_kwh"]) for r in rows}
        models = ["mlp", "gru", "lstm", "tcn", "timexer"]
        x = np.arange(5)
        for mode, offset, color in (
            ("target_only", -0.18, "#9aa7b4"),
            ("transfer", 0.18, "#246b82"),
        ):
            ax.bar(
                x + offset,
                [lookup[(m, mode)] for m in models],
                width=0.35,
                color=color,
                label="Target only" if mode == "target_only" else "Source initialization",
            )
        ax.set_xticks(
            x,
            ["MLP", "GRU", "LSTM", "TCN", "Custom\nattention" if author == "cyber" else "TimeXer"],
        )
        ax.set_title(
            "Cyber independent implementation"
            if author == "cyber"
            else "Duc independent implementation"
        )
        ax.set_ylim(0, 10)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Station macro MAE (kWh)")
    axes[1].legend(fontsize=11)
    fig.tight_layout()
    finish(fig, out / "backbone-benchmarks")
    groups = json.loads(
        (ROOT / "docs/reports/issue99-full-scope-20261110/verification.json").read_text()
    )["groups"]
    groupmap = {(g["namespace"], g["history_days"]): g for g in groups}
    fig, axes = plt.subplots(1, 3, figsize=(10, 4.6), sharey=True)
    for ax, method, title in zip(
        axes,
        ("old_adaptive", "static_mix", "fixed_share"),
        ("Original selector", "Static expert blend", "Fixed-share expert blend"),
        strict=True,
    ):
        values = np.asarray(
            [
                [
                    100
                    * (
                        1
                        - groupmap[(ns, h)]["macro_mae"][method]
                        / groupmap[(ns, h)]["macro_mae"]["old_fixed"]
                    )
                    for h in (7, 14, 28)
                ]
                for ns in NAMESPACES
            ]
        )
        im = ax.imshow(values, cmap="RdBu", vmin=-8, vmax=8, aspect="auto")
        for (i, j), v in np.ndenumerate(values):
            ax.text(
                j,
                i,
                f"{v:+.2f}",
                ha="center",
                va="center",
                color="white" if abs(v) > 5.2 else "black",
                fontsize=11,
            )
        ax.set_xticks(range(3), ["7d", "14d", "28d"])
        ax.set_yticks(
            range(7),
            [
                "UrbanEV SZH",
                "CHARGED AMS",
                "CHARGED JHB",
                "CHARGED LOA",
                "CHARGED MEL",
                "CHARGED SPO",
                "CHARGED SZH",
            ],
        )
        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Initial target history")
    fig.subplots_adjust(wspace=0.15, left=0.15, right=0.9, bottom=0.16, top=0.88)
    cax = fig.add_axes([0.925, 0.19, 0.017, 0.64])
    fig.colorbar(im, cax=cax, label="MAE reduction versus Fixed (%)")
    finish(fig, out / "full-scope-gains")
    ordered = [groupmap[(ns, h)] for ns in NAMESPACES for h in (7, 14, 28)]
    controls = json.loads((baseline / "fusion-controls-summary.json").read_text())["groups"]
    controlmap = {(r["namespace"], r["history_days"]): r for r in controls}
    labels = [f"{g['namespace']}  {g['history_days']}d" for g in ordered]
    fig, axes = plt.subplots(1, 3, figsize=(10, 6.3), sharey=True)
    for ax, method, title in zip(
        axes,
        ("static_mix", "equal_weight", "share_only"),
        ("Calibrated static", "Equal weight", "Sharing without loss"),
        strict=True,
    ):
        values = []
        for g in ordered:
            reference = (
                g["macro_mae"][method]
                if method == "static_mix"
                else controlmap[(g["namespace"], g["history_days"])][method]
            )
            values.append(100 * (reference - g["macro_mae"]["fixed_share"]) / reference)
        ax.barh(np.arange(21), values, color=["#246b82" if x > 0 else "#bb6546" for x in values])
        ax.axvline(0, color="black", lw=0.8)
        ax.set_yticks(range(21), labels, fontsize=11)
        ax.invert_yaxis()
        ax.set_xlabel("MAE reduction (%)", fontsize=11)
        ax.grid(axis="x", alpha=0.2)
        ax.set_axisbelow(True)
        ax.set_title(title, fontsize=12)
        ax.tick_params(axis="x", labelsize=10)
    fig.tight_layout()
    finish(fig, out / "incremental-controller")
    # Deterministic examples: median station-level gain at 14d, paired seed 42.
    manifest = {
        r["path"]: r["sha256"]
        for r in json.loads((args.full_run / "readback-v1/artifact-manifest.json").read_text())
    }
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.1))
    trajectory_rows = []
    selection = []
    for row_index, ns in enumerate(("charged-JHB", "urbanev-SZH")):
        group = next(
            g
            for g in json.loads((args.full_run / "summary.json").read_text())["groups"]
            if g["namespace"] == ns and g["history_days"] == 14
        )
        eligible = [
            (100 * (m["old_fixed"] - m["fixed_share"]) / m["old_fixed"], target)
            for target, m in group["station_means"].items()
            if m["old_fixed"] is not None and m["old_fixed"] > 1e-4
        ]
        gain, target = sorted(eligible)[len(eligible) // 2]
        path = args.full_run / f"{ns}-14d/cell-{target}-42.json"
        if digest(path) != manifest[str(path)]:
            raise ValueError("Selected trajectory differs from verified artifact")
        record = json.loads(path.read_text())
        cell = record["cell"]
        stable = np.abs(np.asarray(cell["stable"]) - cell["labels"]).mean(axis=1)
        dates = [datetime.fromisoformat(o).replace(tzinfo=None) for o in cell["origins"]]
        weights = record["arms"]["fixed_share"]["weights"]
        ax = axes[row_index, 0]
        ax.plot(dates, weights, color="#246b82", label="Adaptive stable weight")
        ax.axhline(0.4307815378871372, color="#999999", ls="--", label="Static weight")
        ax.set_ylim(0.1, 0.9)
        ax.set_ylabel("Stable expert weight")
        ax.set_title(f"{ns} target {target}, 14d, seed 42", fontsize=12)
        ax.grid(alpha=0.2)
        ax = axes[row_index, 1]
        for method, errors, color in (
            ("Fixed", stable, "#666666"),
            ("Static blend", record["arms"]["static_mix"]["daily_mae"], "#b17d38"),
            ("Fixed-share", record["arms"]["fixed_share"]["daily_mae"], "#246b82"),
        ):
            cumulative = np.cumsum(errors) / np.arange(1, len(dates) + 1)
            ax.plot(dates, cumulative, color=color, label=method)
        ax.set_ylabel("Cumulative MAE (kWh)")
        ax.set_title("Scored days only", fontsize=12)
        ax.grid(alpha=0.2)
        for origin, w, s, a, b in zip(
            cell["origins"],
            weights,
            stable,
            record["arms"]["fixed_share"]["daily_mae"],
            record["arms"]["static_mix"]["daily_mae"],
            strict=True,
        ):
            trajectory_rows.append(
                {
                    "namespace": ns,
                    "target": target,
                    "seed": 42,
                    "origin": origin,
                    "stable_weight": w,
                    "fixed_daily_mae": s,
                    "adaptive_daily_mae": a,
                    "static_daily_mae": b,
                }
            )
        selection.append(
            {
                "namespace": ns,
                "target": target,
                "history_days": 14,
                "seed": 42,
                "station_seed_averaged_reduction_percent": gain,
                "cell_sha256": digest(path),
                "selection": "Upper median station gain among stable MAE > 1e-4, 14d; fixed seed 42",
            }
        )
    axes[0, 0].legend(fontsize=10)
    axes[0, 1].legend(fontsize=10)
    import matplotlib.dates as mdates

    for ax in axes.flat:
        locator = mdates.AutoDateLocator(minticks=3, maxticks=5)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.tick_params(axis="x", labelsize=11)
    fig.tight_layout()
    finish(fig, out / "controller-trajectories")
    with (args.output / "trajectory-data.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(trajectory_rows[0]))
        writer.writeheader()
        writer.writerows(trajectory_rows)
    (args.output / "trajectory-selection.json").write_text(json.dumps(selection, indent=2))
    for index, expression in enumerate(
        re.findall(r"\$\$(.*?)\$\$", (args.output / "manuscript.md").read_text(), re.S), 1
    ):
        if "\\begin{cases}" in expression:
            expression = r"\lambda_{t+1}=\lambda_b\ \mathrm{if}\ n\geq5\ \mathrm{and}\ \mathrm{LCB}_{0.025}>0;\quad\lambda_a\ \mathrm{otherwise}"
        fig = plt.figure(figsize=(9, 0.65))
        fig.patch.set_alpha(0)
        fig.text(0.01, 0.5, "$" + expression.strip() + "$", fontsize=14, va="center")
        fig.savefig(
            out / f"equation-{index}.png",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.04,
            transparent=True,
        )
        plt.close(fig)
        figures.append(index)
    print(json.dumps({"equations": len(figures), "trajectory_selection": selection}))


if __name__ == "__main__":
    main()
