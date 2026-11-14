"""Render publication figures from the recorded issue99 result tables."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BLUE, CORAL, GRAY = "#2166ac", "#d6604d", "#69717b"
NAMESPACES = [
    "urbanev-SZH",
    "charged-AMS",
    "charged-JHB",
    "charged-LOA",
    "charged-MEL",
    "charged-SPO",
    "charged-SZH",
]


def rows(path: Path) -> list[dict]:
    """Read a recorded UTF-8 CSV without modifying its contents."""
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def save(figure: plt.Figure, output: Path, name: str) -> None:
    """Save a vector publication asset and a matching review preview."""
    for suffix in ("pdf", "png"):
        figure.savefig(output / f"{name}.{suffix}", dpi=240, bbox_inches="tight", pad_inches=0.06)
    plt.close(figure)


def baseline_figure(output: Path) -> None:
    """Show each implementation's paired initialization comparison separately."""
    folder = ROOT / "docs/reports/issue99-teacher-review-20261111"
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharex=True)
    for ax, author, title in zip(
        axes, ("cyber", "duc"), ("(a) Implementation A", "(b) Implementation B"), strict=True
    ):
        lookup = {
            (r["model"].lower(), r["mode"]): float(r["mae_kwh"])
            for r in rows(folder / f"{author}-summary.csv")
        }
        models = ["mlp", "gru", "lstm", "tcn", "timexer"]
        for index, name in enumerate(models):
            local, transfer = [lookup[name, mode] for mode in ("target_only", "transfer")]
            ax.plot([transfer, local], [index, index], color="#ced6d9", lw=2.1)
            ax.scatter(
                local,
                index,
                color=GRAY,
                s=28,
                label="Target only" if index == 0 else None,
                zorder=3,
            )
            ax.scatter(
                transfer,
                index,
                color=BLUE,
                marker="s",
                s=28,
                label="Source initialized" if index == 0 else None,
                zorder=3,
            )
        ax.set_yticks(
            range(5),
            [
                "MLP",
                "GRU",
                "LSTM",
                "TCN",
                "Custom attention" if author == "cyber" else "Official TimeXer",
            ],
        )
        ax.set_ylim(4.6, -0.6)
        ax.set_xlim(4.8, 9.4)
        ax.set_xticks([5, 6, 7, 8, 9])
        ax.set_xlabel("MAE (kWh); lower is better")
        ax.set_title(title, loc="left", fontweight="bold", pad=10)
        ax.grid(axis="x", color="#e8ecee")
        ax.set_axisbelow(True)
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        loc="lower center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, -0.06),
    )
    fig.subplots_adjust(wspace=0.8, left=0.15, right=0.98, bottom=0.22, top=0.86)
    save(fig, output, "backbones")


def calibration_figure(output: Path) -> None:
    """Show all registered epoch candidates, including adverse larger budgets."""
    evidence = ROOT / "docs/reports/issue99-history-review-20261110"
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    epochs = (3, 10, 30, 100, 300)
    for ax, history in zip(axes, (7, 14, 28), strict=True):
        lock = json.loads((evidence / f"{history}d-epoch-lock.json").read_text())
        for method, color, marker, label in (
            ("target_only", GRAY, "o", "Target only"),
            ("source_finetune", BLUE, "s", "Source initialized"),
        ):
            chosen = lock["chosen"][method]
            values = [chosen["curve"][str(e)] for e in epochs]
            ax.plot(epochs, values, marker=marker, color=color, lw=1.5, ms=4, label=label)
            ax.scatter(
                chosen["epochs"],
                chosen["calibration_mae"],
                marker="*",
                s=90,
                color=CORAL,
                zorder=4,
            )
        ax.set_xscale("log")
        ax.set_xticks(epochs, labels=[str(e) for e in epochs])
        ax.minorticks_off()
        ax.set_ylim(4.9, 10)
        ax.set_xlabel("Initial epochs")
        ax.set_title(f"{history}-day history", loc="left", fontweight="bold")
        ax.grid(axis="y", color="#e8ecee")
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Calibration MAE (kWh)")
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(plt.Line2D([], [], color=CORAL, marker="*", ls="", ms=8))
    labels.append("Selected candidate")
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, -0.05),
        fontsize=9,
    )
    fig.subplots_adjust(wspace=0.2, left=0.09, right=0.99, bottom=0.24, top=0.87)
    save(fig, output, "calibration")


def cohort_figure(output: Path) -> None:
    """Distinguish gains over one retained expert from the weighting increment."""
    source = rows(ROOT / "docs/reports/issue99-full-scope-20261110/group-results.csv")
    lookup = {(r["namespace"], int(r["history_days"])): r for r in source}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
    for ax, reference, title, limit in zip(
        axes,
        ("old_fixed", "static_mix"),
        ("(a) Adaptive vs. single Fixed", "(b) Adaptive vs. static mixture"),
        (8.0, 0.6),
        strict=True,
    ):
        values = np.array(
            [
                [
                    100
                    * (1 - float(lookup[ns, h]["fixed_share"]) / float(lookup[ns, h][reference]))
                    for h in (7, 14, 28)
                ]
                for ns in NAMESPACES
            ]
        )
        im = ax.pcolormesh(
            np.arange(4) - 0.5,
            np.arange(8) - 0.5,
            values,
            vmin=-limit,
            vmax=limit,
            cmap="RdBu",
            shading="flat",
            rasterized=False,
        )
        ax.set_xlim(-0.5, 2.5)
        ax.set_ylim(6.5, -0.5)
        for (i, j), value in np.ndenumerate(values):
            ax.text(
                j,
                i,
                f"{value:+.2f}",
                ha="center",
                va="center",
                fontsize=9.5,
                color="white" if abs(value) > limit * 0.65 else "#18252b",
            )
        ax.set_yticks(
            range(7),
            [
                "UrbanEV / SZH",
                "CHARGED / AMS",
                "CHARGED / JHB",
                "CHARGED / LOA",
                "CHARGED / MEL",
                "CHARGED / SPO",
                "CHARGED / SZH",
            ],
        )
        ax.set_xticks(range(3), ["7 days", "14 days", "28 days"])
        ax.set_xlabel("Initial target history")
        ax.set_title(title, fontsize=10, loc="left", fontweight="bold", pad=10)
        colorbar = fig.colorbar(
            im,
            ax=ax,
            orientation="horizontal",
            pad=0.22,
            fraction=0.05,
            label="MAE reduction (%)",
            ticks=[-limit, 0, limit],
        )
        colorbar.solids.set_rasterized(False)
        colorbar.solids.set_edgecolor("face")
    fig.subplots_adjust(wspace=0.2, left=0.23, right=0.99, bottom=0.1, top=0.89)
    save(fig, output, "cohort-comparisons")


def trajectory_figure(output: Path) -> None:
    """Plot both recorded examples, using complete dates and original energy units."""
    source = rows(ROOT / "report/teacher-review-20261111/trajectory-data.csv")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8))
    for index, namespace in enumerate(("charged-JHB", "urbanev-SZH")):
        selected = [r for r in source if r["namespace"] == namespace]
        dates = [datetime.fromisoformat(r["origin"]) for r in selected]
        weights = [float(r["stable_weight"]) for r in selected]
        ax = axes[index, 0]
        ax.plot(dates, weights, color=BLUE, lw=1.6, label="Adaptive weight")
        ax.axhline(0.4307815378871372, color=GRAY, ls="--", lw=1, label="Static weight")
        ax.set_ylim(0.1, 0.9)
        ax.set_ylabel("Stable weight")
        ax.set_title(f"{namespace}; ID {selected[0]['target']}", loc="left", fontweight="bold")
        ax = axes[index, 1]
        for field, label, color, style in (
            ("fixed_daily_mae", "Fixed", GRAY, "-"),
            ("static_daily_mae", "Static mixture", CORAL, "--"),
            ("adaptive_daily_mae", "Adaptive mixture", BLUE, "-"),
        ):
            errors = np.asarray([float(r[field]) for r in selected])
            ax.plot(
                dates,
                np.cumsum(errors) / np.arange(1, len(errors) + 1),
                label=label,
                color=color,
                ls=style,
                lw=1.5,
            )
        ax.set_ylabel("Cumulative MAE (kWh)")
        ax.set_title("Same scored origins", loc="left", fontweight="bold")
        for ax in axes[index]:
            locator = mdates.AutoDateLocator(minticks=3, maxticks=4)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            years = (
                str(dates[0].year)
                if dates[0].year == dates[-1].year
                else f"{dates[0].year}–{dates[-1].year}"
            )
            ax.set_xlabel(f"Forecast origin ({years})")
            ax.grid(color="#e8ecee")
            ax.set_axisbelow(True)
    axes[0, 0].legend(fontsize=8, frameon=False, loc="upper left")
    axes[0, 1].legend(fontsize=8, frameon=False, loc="upper right")
    fig.subplots_adjust(left=0.1, right=0.99, top=0.92, bottom=0.1, wspace=0.35, hspace=0.65)
    save(fig, output, "trajectories")


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 10,
            "pdf.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#adb5ba",
            "text.color": "#18252b",
            "axes.labelcolor": "#18252b",
        }
    )
    baseline_figure(args.output)
    calibration_figure(args.output)
    cohort_figure(args.output)
    trajectory_figure(args.output)


if __name__ == "__main__":
    main()
