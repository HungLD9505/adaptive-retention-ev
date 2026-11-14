"""Plot registered calibration values and verified paired-history comparisons."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
TEAL, GRAY, BLUE, AMBER, GREEN = "#096b78", "#59636e", "#315b8a", "#b77132", "#287d69"


def save_figure(figure: plt.Figure, destination: Path) -> None:
    """Export vector PDF and high-resolution PNG with matching contents."""
    for suffix in ("pdf", "png"):
        figure.savefig(destination.with_suffix("." + suffix), dpi=320, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--evidence-root", type=Path, default=ROOT / "docs/reports/issue99-history-review-20261110"
    )
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": "#263544",
            "text.color": "#263544",
            "axes.edgecolor": "#a6aeb6",
            "pdf.fonttype": 42,
        }
    )
    histories = (7, 14, 28)
    epochs = (3, 10, 30, 100, 300)
    records = []
    figure, axes = plt.subplots(1, 3, figsize=(11.4, 3.6), sharey=True)
    for ax, history in zip(axes, histories, strict=True):
        lock = json.loads((args.evidence_root / f"{history}d-epoch-lock.json").read_text())
        for method, color, marker in (
            ("target_only", GRAY, "o"),
            ("source_finetune", TEAL, "s"),
        ):
            chosen = lock["chosen"][method]
            values = [chosen["curve"][str(epoch)] for epoch in epochs]
            records.extend(
                {"history_days": history, "method": method, "epochs": e, "mae_kwh": v}
                for e, v in zip(epochs, values, strict=True)
            )
            ax.plot(epochs, values, color=color, marker=marker, lw=2.1, ms=5)
            selected = chosen["epochs"]
            value = chosen["calibration_mae"]
            assert value == chosen["curve"][str(selected)]
            ax.scatter([selected], [value], marker="*", s=165, color=AMBER, zorder=5)
            ax.annotate(
                f"{selected} epochs\n{value:.3f} kWh",
                (selected, value),
                xytext=((0, 40) if history == 28 else (8, 24))
                if method == "source_finetune"
                else (0, -35),
                textcoords="offset points",
                ha="left" if method == "source_finetune" and history != 28 else "center",
                color=color,
                fontsize=10.5,
                fontweight="bold",
            )
        ax.set_xscale("log")
        ax.set_xticks(epochs, labels=[str(x) for x in epochs])
        ax.minorticks_off()
        ax.set_ylim(4.9, 10.0)
        ax.set_xlim(2.5, 365)
        ax.set_title(f"{history}-day history", fontsize=13, fontweight="bold", pad=11)
        ax.set_xlabel("Initial target epochs")
        ax.grid(axis="y", color="#e7ebef", lw=0.8)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Calibration MAE (kWh)")
    figure.legend(
        handles=[
            Line2D([], [], color=GRAY, marker="o", label="Target only"),
            Line2D([], [], color=TEAL, marker="s", label="Source initialization"),
            Line2D([], [], color=AMBER, marker="*", linestyle="", ms=10, label="Selected epoch"),
        ],
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.52, 1.08),
    )
    figure.subplots_adjust(wspace=0.13, top=0.84, bottom=0.18)
    save_figure(figure, args.output / "epoch-selection")

    summary = json.loads((args.evidence_root / "verified-summary.json").read_text())
    by_history = {row["history_days"]: row["mae"] for row in summary["histories"]}
    figure, (transfer, retention) = plt.subplots(1, 2, figsize=(10.8, 3.8))
    y = np.arange(3)
    target = [by_history[h]["target_only"] for h in histories]
    source = [by_history[h]["source_finetune"] for h in histories]
    for index, (initial, adapted) in enumerate(zip(target, source, strict=True)):
        transfer.plot([adapted, initial], [index, index], color="#d4dde3", lw=3, zorder=1)
        transfer.annotate(
            f"{100 * (initial - adapted) / initial:.2f}% lower",
            ((adapted + initial) / 2, index),
            xytext=(0, -18),
            textcoords="offset points",
            ha="center",
            color=TEAL,
            fontsize=10.5,
            fontweight="bold",
        )
        for value, color in ((initial, GRAY), (adapted, TEAL)):
            transfer.annotate(
                f"{value:.4f}",
                (value, index),
                xytext=(0, 11),
                textcoords="offset points",
                ha="center",
                fontsize=10.5,
                color=color,
            )
    transfer.scatter(target, y, s=62, color=GRAY, label="Target only", zorder=3)
    transfer.scatter(source, y, s=62, color=TEAL, label="Source fine-tuning", zorder=3)
    transfer.set_yticks(y, labels=[f"{h} days" for h in histories])
    transfer.set_ylim(2.45, -0.45)
    transfer.set_xlim(3.0, 5.55)
    transfer.set_xlabel("Station macro MAE (kWh)")
    transfer.set_title("Transfer benefit", fontweight="bold", pad=12)
    transfer.spines["left"].set_visible(False)
    transfer.grid(axis="x", color="#eef1f4")
    transfer.set_axisbelow(True)
    transfer.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.24), frameon=False, ncol=2, fontsize=10
    )
    gains = {}
    for method, name, color, marker, style in (
        ("fixed_bank", "Fixed retention", BLUE, "s", "-"),
        ("mean_only", "Past-error selection", AMBER, "o", ":"),
        ("confidence_gate", "Confidence gate", GREEN, "^", "--"),
    ):
        values = [
            100
            * (by_history[h]["source_finetune"] - by_history[h][method])
            / by_history[h]["source_finetune"]
            for h in histories
        ]
        gains[method] = values
        retention.plot(
            histories, values, color=color, marker=marker, ls=style, lw=2, ms=7, label=name
        )
    for index, history in enumerate(histories):
        best = max(gains, key=lambda key: gains[key][index])
        value = gains[best][index]
        retention.annotate(
            f"{value:.2f}%",
            (history, value),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            fontsize=10.5,
            fontweight="bold",
        )
    retention.axhline(0, color="#aab4bc", lw=0.9)
    retention.set_xticks(histories, labels=[str(h) for h in histories])
    retention.set_xlim(5, 30)
    retention.set_ylim(-0.12, 1.85)
    retention.set_title("Retention benefit", fontweight="bold", pad=12)
    retention.set_ylabel("MAE reduction vs fine-tuning (%)")
    retention.set_xlabel("Initial history (days)")
    retention.grid(axis="y", color="#eef1f4")
    retention.set_axisbelow(True)
    retention.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.24), frameon=False, ncol=1, fontsize=10
    )
    figure.subplots_adjust(wspace=0.38, bottom=0.25, top=0.86)
    save_figure(figure, args.output / "history-comparison")
    (args.output / "comparison-chart-values.json").write_text(
        json.dumps(
            {"calibration": records, "history_mae": by_history, "retention_gain_percent": gains},
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
