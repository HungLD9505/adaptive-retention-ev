"""Export verified issue99 measurements and paper-ready exploratory figures."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ev_models.checkpoint import digest
from ev_runner.replay import Replay
from ev_search.comparison import METHODS, SEEDS, TARGETS
from ev_search.comparison_verify import _scores, verify_matrix
from ev_search.fixed import FixedSearchConfig
from ev_search.ledger import FixedLedger
from tools.issue99_costs import summarize
from tools.issue99_study import verify_run
from tools.issue99_study_support import PreparedInputs


def write_csv(path: Path, rows: list[dict]) -> None:
    """Create a full-precision measurement table."""
    if not rows:
        return
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def events(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for p in sorted(path.glob("tick-*/events.jsonl"))
        for line in p.read_text().splitlines()
    ]


def fixed_tables(root: Path, out: Path, replays: dict[str, Replay]) -> tuple[list[dict], float]:
    """Export every measured fixed point and its sampled diagnostic category."""
    fixed = [json.loads(line) for line in (root / "fixed/events.jsonl").read_text().splitlines()]
    fixed = [e for e in fixed if e["event"] == "trial_end"]
    baseline = next(e["outcome"]["objective_mae_kwh"] for e in fixed if e["lambda"] == 0)
    trials, cells, diagnostics = [], [], []
    for event in fixed:
        score = event["outcome"]["objective_mae_kwh"]
        trial = {
            "trial": event["trial"],
            "lambda": event["lambda"],
            "role": event["role"],
            "status": event["status"],
            "failure_reason": event["outcome"].get("error"),
            "calibration_mae_kwh": score,
            "delta_vs_lambda0_kwh": score - baseline if score is not None else None,
        }
        ratios, displacements = [], []
        for cell in event["outcome"].get("runs", []):
            # Run paths are archived verbatim; resolve them relative to this restore.
            path = (
                root
                / "fixed"
                / f"trial-{event['trial']:04d}"
                / f"target-{cell['target']}-seed-{cell['seed']}"
            )
            report = json.loads((path / "run.json").read_text())
            if digest(path / "run.json") != cell["run_sha256"]:
                raise ValueError("Restored calibration report hash differs")
            verify_run(path, report, replays[cell["target"]])
            cells.append(
                {
                    "trial": event["trial"],
                    "lambda": event["lambda"],
                    "target": cell["target"],
                    "seed": cell["seed"],
                    "mae_kwh": report["mae_kwh"],
                    "rmse_kwh": report["rmse_kwh"],
                    "objective_scored_days": report["objective_scored_days"],
                    "invocation_wall_seconds": report["invocation_wall_seconds"],
                }
            )
            for item in events(path):
                if item["event"] == "loss_gradient":
                    ratios.append(item["weighted_gradient_ratio"])
                    displacements.append(item["latent_displacement_mse"])
                    diagnostics.append(
                        {
                            "trial": event["trial"],
                            "target": cell["target"],
                            "seed": cell["seed"],
                            **{k: v for k, v in item.items() if k != "event"},
                        }
                    )
        trial["median_local_gradient_ratio"] = statistics.median(ratios) if ratios else None
        trial["median_latent_displacement_mse"] = (
            statistics.median(displacements) if displacements else None
        )
        trials.append(trial)
    trials.sort(key=lambda r: r["lambda"])
    write_csv(out / "fixed-trials.csv", trials)
    write_csv(out / "fixed-station-seed.csv", cells)
    write_csv(out / "fixed-diagnostics.csv", diagnostics)
    # These are sampled descriptive categories, not inferred continuous thresholds.
    regimes = defaultdict(list)
    for row in trials:
        if row["calibration_mae_kwh"] is None or row["lambda"] == 0:
            continue
        direction = (
            "lower_observed_MAE"
            if row["delta_vs_lambda0_kwh"] < -1e-12
            else "higher_observed_MAE"
            if row["delta_vs_lambda0_kwh"] > 1e-12
            else "numerical_tie"
        )
        ratio = row["median_local_gradient_ratio"]
        strength = (
            "forecast_gradient_larger"
            if ratio is not None and ratio < 1
            else "retention_gradient_larger"
        )
        regimes[(direction, strength)].append(row)
    regime_rows = []
    for (direction, strength), rows in regimes.items():
        representative = rows[len(rows) // 2]
        regime_rows.append(
            {
                "observed_error_direction": direction,
                "local_gradient_category": strength,
                "sampled_min_lambda": min(r["lambda"] for r in rows),
                "sampled_max_lambda": max(r["lambda"] for r in rows),
                "measured_points": len(rows),
                "representative_evaluated_lambda": representative["lambda"],
                "representative_calibration_mae_kwh": representative["calibration_mae_kwh"],
                "representative_median_gradient_ratio": representative[
                    "median_local_gradient_ratio"
                ],
                "qualification": "Sample support only; may be disconnected; no continuous boundary or significance claim",
            }
        )
    write_csv(out / "fixed-regimes.csv", regime_rows)
    return trials, baseline


def comparison_tables(
    root: Path,
    out: Path,
    jobs: list[dict],
    protocol: dict,
    replays: dict[str, Replay],
    checked: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Export paired original-unit errors without reselecting on later outcomes."""
    run_rows, daily, trajectories = [], [], []
    for job in jobs:
        job_record = json.loads((root / "comparison" / job["job_id"] / "job.json").read_text())
        path = root / "comparison" / job_record["run_path"]
        report = json.loads((path / "run.json").read_text())
        _, errors = _scores(
            path, {**job, "report_levels": report.get("candidate_levels")}, replays[job["target"]]
        )
        evaluation = set(job["evaluation_origins"]) & errors.keys()
        mae = sum(errors[o][0] for o in evaluation) / len(evaluation)
        rmse = math.sqrt(sum(errors[o][1] for o in evaluation) / len(evaluation))
        full = sum(v[0] for v in errors.values()) / len(errors)
        run_rows.append(
            {
                "method": job["method"],
                "target": job["target"],
                "seed": job["seed"],
                "evaluation_mae_kwh": mae,
                "evaluation_rmse_kwh": rmse,
                "evaluation_days": len(evaluation),
                "full90_descriptive_mae_kwh": full,
                "issued_days": report["issued_days"],
                "scored_days": report["scored_days"],
                "reused_from": job["reuse_job_id"],
                "run_sha256": digest(path / "run.json"),
            }
        )
        cal = set(protocol["calibration_origins"][job["target"]])
        for origin, (error, mse) in sorted(errors.items()):
            daily.append(
                {
                    "method": job["method"],
                    "target": job["target"],
                    "seed": job["seed"],
                    "origin": origin,
                    "phase": "evaluation"
                    if origin in evaluation
                    else "calibration"
                    if origin in cal
                    else "embargo",
                    "mae_kwh": error,
                    "mse_kwh2": mse,
                }
            )
        for forecast in sorted(path.glob("tick-*/forecasts.json")):
            row = json.loads(forecast.read_text())
            if row:
                value = row.get("lambda", row.get("active"))
                trajectories.append(
                    {
                        "method": job["method"],
                        "target": job["target"],
                        "seed": job["seed"],
                        "origin": row["origin"],
                        "lambda": value,
                    }
                )
    write_csv(out / "comparison-runs.csv", run_rows)
    write_csv(out / "daily-errors.csv", daily)
    write_csv(out / "lambda-trajectories.csv", trajectories)
    summary = []
    for method in METHODS:
        rows = [r for r in run_rows if r["method"] == method]
        seed_means = [
            statistics.mean(r["evaluation_mae_kwh"] for r in rows if r["seed"] == seed)
            for seed in SEEDS
        ]
        summary.append(
            {
                "method": method,
                "evaluation_mae_kwh": checked["aggregate_mae_kwh"][method],
                "full90_descriptive_mae_kwh": statistics.mean(
                    r["full90_descriptive_mae_kwh"] for r in rows
                ),
                "paired_seed_aggregate_min": min(seed_means),
                "paired_seed_aggregate_max": max(seed_means),
            }
        )
    write_csv(out / "method-summary.csv", summary)
    return summary, daily, trajectories


def draw_figures(
    out: Path,
    protocol: dict,
    trials: list[dict],
    baseline: float,
    selected: dict,
    summary: list[dict],
    trajectories: list[dict],
    daily: list[dict],
) -> None:
    """Render standalone measured curves and calendar-aligned trajectories."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.1), layout="constrained")
    valid = [r for r in trials if r["calibration_mae_kwh"] is not None]
    axes[0].plot(
        [r["lambda"] for r in valid], [r["calibration_mae_kwh"] for r in valid], "o-", lw=1, ms=4
    )
    axes[0].axhline(baseline, color="gray", ls="--", label="lambda=0")
    axes[0].set_xscale("symlog", linthresh=protocol["fixed_search"]["positive_lower"] / 2)
    axes[0].set(
        xlabel="Fixed lambda (measured points)",
        ylabel="Calibration MAE (kWh)",
        title="Fixed sensitivity: exploratory Development",
    )
    axes[0].legend()
    for name, key in [
        ("Penalty-gradient ratio", "median_local_gradient_ratio"),
        ("Latent displacement MSE", "median_latent_displacement_mse"),
    ]:
        p = [r for r in valid if r["lambda"] > 0 and r[key] is not None]
        axes[1].plot([r["lambda"] for r in p], [r[key] for r in p], "o-", label=name)
    axes[1].set_xscale("log")
    axes[1].set_yscale("symlog", linthresh=1e-5)
    axes[1].set(
        xlabel="Fixed lambda",
        ylabel="Median sampled diagnostic",
        title="Arrived-label diagnostics (every 7 days)",
    )
    axes[1].legend(fontsize=8)
    fig.savefig(out / "fixed-sensitivity.png", dpi=180)
    fig.savefig(out / "fixed-sensitivity.pdf")
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), layout="constrained")
    for ax, target in zip(axes.flat, TARGETS, strict=True):
        for seed in SEEDS:
            rows = [
                r
                for r in trajectories
                if r["method"] == "continuous" and r["target"] == target and r["seed"] == seed
            ]
            by_day = {
                (
                    datetime.fromisoformat(r["origin"])
                    - datetime.fromisoformat(protocol["calibration_origins"][target][0])
                ).days: r["lambda"]
                for r in rows
            }
            ax.plot(
                range(90),
                [by_day.get(i, float("nan")) for i in range(90)],
                label=f"Seed {seed}",
                lw=1,
            )
        errors_by_day = defaultdict(list)
        for item in daily:
            if item["method"] == "continuous" and item["target"] == target:
                index = (
                    datetime.fromisoformat(item["origin"])
                    - datetime.fromisoformat(protocol["calibration_origins"][target][0])
                ).days
                errors_by_day[index].append(item["mae_kwh"])
        right = ax.twinx()
        right.plot(
            range(90),
            [
                statistics.mean(errors_by_day[i]) if errors_by_day[i] else float("nan")
                for i in range(90)
            ],
            color="black",
            alpha=0.25,
            lw=0.8,
        )
        right.set_ylabel("Forecast MAE (kWh)", fontsize=8)
        ax.axvspan(0, 29.5, color="gray", alpha=0.08)
        ax.axvline(29.5, color="gray", ls=":", lw=0.8)
        ax.axhline(selected["selected_lambda"], color="black", ls="--", lw=0.7, label="Fixed")
        ax.set(
            title=f"Target {target}",
            xlabel="Scheduled day (missing forecasts leave gaps)",
            ylabel="Lambda",
        )
        ax.legend(fontsize=7)
    fig.savefig(out / "controller-trajectories.png", dpi=180)
    fig.savefig(out / "controller-trajectories.pdf")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.bar(
        [r["method"] for r in summary],
        [r["evaluation_mae_kwh"] for r in summary],
        color=["#6c757d", "#457b9d", "#e9c46a", "#2a9d8f", "#8e7dbe"],
    )
    ax.set(
        ylabel="Later-objective MAE (kWh)",
        title="Exploratory later Development objective, station-first mean",
    )
    ax.tick_params(axis="x", rotation=15)
    fig.savefig(out / "method-comparison.png", dpi=180)
    fig.savefig(out / "method-comparison.pdf")
    plt.close(fig)


def write_handoff(
    out: Path, checked: dict, selected: dict, controller: dict, summary: list[dict]
) -> None:
    """Write the measured result table with its scope and interpretation limits."""
    evaluation0 = checked["aggregate_mae_kwh"]["lambda0"]
    table = "| Method | Later-objective MAE, kWh | Delta vs lambda0 | Full-90 descriptive MAE |\n| --- | ---: | ---: | ---: |\n"
    for row in summary:
        table += f"| {row['method']} | {row['evaluation_mae_kwh']:.6f} | {row['evaluation_mae_kwh'] - evaluation0:+.6f} | {row['full90_descriptive_mae_kwh']:.6f} |\n"
    paired_delta = (
        checked["aggregate_mae_kwh"]["continuous"] - checked["aggregate_mae_kwh"]["fixed"]
    )
    station_table = "| Target | lambda0 | Fixed | Discrete | Continuous | Frozen |\n| --- | ---: | ---: | ---: | ---: | ---: |\n"
    for target in TARGETS:
        station_table += (
            "| "
            + target
            + " | "
            + " | ".join(f"{checked['targets'][target][method]:.6f}" for method in METHODS)
            + " |\n"
        )
    text = f"""# Issue #99 completed exploratory Development study

This study compares calibrated fixed latent retention with a continuous one-step validation controller. On the registered later objective, Continuous MAE is {checked["aggregate_mae_kwh"]["continuous"]:.6f} kWh and Fixed MAE is {checked["aggregate_mae_kwh"]["fixed"]:.6f} kWh. Source10, four selected UrbanEV/SZH targets, three paired seeds and 14-day initial history were reused. This is exploratory Development evidence, not fresh held-out or scientifically peer-approved evidence. The task remains 24→24. Historical reports and Final results are unchanged.

## Registered scope and selection

The first 28 scheduled origins supplied calibration, the next two were excluded from both score objectives, and the final 60 supplied the later objective. Online replay covered all 90 scheduled days with actual delayed label availability. Prior exposure to this cohort makes every result exploratory. Expected later score counts are 60/22/22/22, not 60 complete days for every station; all missing/skipped outcomes remain.

Fixed selection: lambda={selected["selected_lambda"]:.12g}, calibration MAE={selected["mae_kwh"]:.9f} kWh versus lambda0={selected["lambda0_mae_kwh"]:.9f}. Boundary unresolved: {selected["upper_boundary_unresolved"]}. The selected value is best among evaluated points, not a proven global optimum. The full fixed ledger, failed/null trials and sampled regimes are exported separately; sensitivity lines connect measurements and do not estimate exact transition boundaries.

Controller interval: [0,{selected["controller_upper_bound"]:.12g}], initialized at {selected["selected_lambda"]:.12g}. Selected eta={controller["selected"]["eta"]:.12g}, cadence={controller["selected"]["cadence"]} complete arrivals, A=2 older arrived days and V=1 newer untrained day. Selection used only registered calibration MAE among six declared recipes. The numerical bounds and scale fractions are study choices; cited hypergradient papers do not prescribe EV-specific values.

## Matched results

{table}
Continuous minus calibrated Fixed on the later objective is **{paired_delta:+.6f} kWh**; a negative value favors Continuous. This is the main mechanism comparison, not the earlier calibration improvement.

{station_table}
All entries average paired seeds within station, then give the four stations equal weight. The full-90 column mixes calibration and later days and is descriptive only. Frozen lambda may exactly reuse Fixed when all executable configurations match; it is not an independently retrained replicate. The legacy discrete controller keeps its original recipe and three shadow models, with greater compute and different initialization than the single-branch methods. It was not retuned for this new calibration split, so tuning budgets differ and its gap cannot be attributed solely to the controller mechanism.

## Interpretation and limits

Read the paired station results and seed ranges with the aggregate. Four historically selected stations in one city are a small dependent cohort. No significance, universal transfer/GRU superiority, or calibrated safe-adaptation guarantee is established. Coefficient movement and gradient ratios are diagnostics, not proof of forecast improvement. Negative comparisons remain visible. This study does not replace the separate backbone/transfer baseline work in issue #97.

The implemented loss/update formulas and paper attribution remain in the preceding verification handoff. Fixed uses a constant real coefficient; continuous uses a projected one-step current-Adam validation hypergradient with a frozen Source encoder/reference scale. No custom GRU cell or silent loss redesign was introduced.

## Verification and artifacts

The independent matrix verifier recomputed saved-prediction errors from authenticated complete arrived labels, required exact method/seed/target identities, matched scored origins and checked each retained tick commitment. It permits explicitly pruned historical states under latest-only retention, while checking the newest full checkpoint. Input bytes were rehashed after execution and report extraction. Runtime/source/code/config hashes are in the run bindings. Publisher raw archives were not freshly checked.

See CSV/JSON records for full precision, costs, coverage, regimes, per-day errors and trajectories; PNG/PDF figures are standalone export artifacts. Historical Source pretraining/billing totals are unknown and must not be reconstructed from update counts. Owner execution authorization does not waive the repository's merge policy.
"""
    (out / "study-results.md").write_text(text)
    method = r"""# Method addition for exploratory retention study

Let F be the mean absolute error across complete normalized 24-hour forecast days and R the frozen-source latent penalty:

$$F(B;\theta)=\frac{1}{24|B|}\sum_{i\in B}\sum_{j=1}^{24}|\hat y_{ij}^{scaled}(\theta)-y_{ij}^{scaled}|,\qquad R(B;\theta)=\frac{1}{64|B|}\sum_{i\in B}\sum_{k=1}^{64}\left(\frac{h_k(x_i;\theta)-h_k(x_i;\theta_s)}{s_k+\epsilon_R}\right)^2.$$

Source parameters theta_s and population latent standard deviations s remain frozen; epsilon_R=0.001. The division occurs before squaring. Fixed trains with F+lambda R using a constant real coefficient. The model remains the existing two-layer, 64-unit GRU and calendar-aware head; no custom GRU cell is introduced. Lambda changes the retention penalty, not the learning rate, and is not a percentage of retained knowledge.

The one-step controller follows the validation-hypergradient rationale of [Luketina et al. (2016)](https://proceedings.mlr.press/v48/luketina16.pdf), specialized here to current-Adam dynamics. From the current real weights/moments, form g(lambda)=grad_theta[F_A+lambda R_A], virtual moments m'=beta1*m+(1-beta1)*g and v'=beta2*v+(1-beta2)*g^2, and a bias-corrected Adam virtual update. Previous weights and moments are treated as fixed starting state for this local derivative; the virtual update does not mutate the real optimizer.

$$\tilde\theta_t(\lambda)=\operatorname{AdamStep}(\theta_t,m_t,v_t;\nabla_\theta[F_A+\lambda R_A]),\qquad\lambda_{t+1}=\Pi_{[0,U]}\left(\lambda_t-\eta\frac{\partial F_V(\tilde\theta_t(\lambda))}{\partial\lambda}\bigg|_{\lambda_t}\right).$$

A contains two older complete arrived label days; V contains the newest complete arrived day not yet used in real training. The outer loss is forecast MAE alone. After the meta decision, the real branch trains on the newly arrived day and marks its label consumed, then issues future forecasts. Learning rate 0.001, Adam betas (0.9,0.999) and Adam epsilon 1e-8 remain fixed; these differ from retention epsilon_R. The exact-zero variance treatment is the documented tested numerical choice, not a convergence guarantee.

Fixed uses finite GP/EI optimization in log-positive lambda plus a separately evaluated zero and a coverage sensitivity grid, following the hyperparameter-optimization rationale of [Snoek et al. (2012)](https://arxiv.org/pdf/1206.2944). The 4097-point acquisition grid approximates maximization of EI over the numeric domain. Numerical endpoints, kernel/noise choices, finite budgets, gradient-derived step scaling and projection are study choices, not EV-specific constants established by these papers. The registered calibration determines Fixed and controller settings before later exploratory comparison.

"""
    (out / "paper-method-and-results.md").write_text(method + "\n" + text)

    latex = "\\begin{tabular}{lrr}\nMethod & MAE (kWh) & Delta vs FT \\\\\n\\hline\n"
    for row in summary:
        latex += f"{row['method'].replace('_', ' ')} & {row['evaluation_mae_kwh']:.4f} & {row['evaluation_mae_kwh'] - evaluation0:+.4f} \\\\\n"
    (out / "paper-results-table.tex").write_text(latex + "\\end{tabular}\n")


def build(args: argparse.Namespace) -> None:
    root, out = args.study, args.output
    out.mkdir(exist_ok=False)
    protocol_path = root / "protocol-lock.json"
    protocol = json.loads(protocol_path.read_text())
    inputs = PreparedInputs(args.inputs, protocol["input_manifest_sha256"])
    jobs = json.loads((root / "comparison-jobs.json").read_text())
    checked = verify_matrix(jobs, root / "comparison", inputs, protocol_path)
    (out / "independent-verification.json").write_text(json.dumps(checked, indent=2) + "\n")
    replays = {target: Replay(inputs, target, 90) for target in TARGETS}
    ledger_metadata = json.loads((root / "fixed/config.json").read_text())
    if ledger_metadata["binding"]["protocol_sha256"] != digest(protocol_path):
        raise ValueError("Fixed ledger protocol hash differs")
    FixedLedger(
        root / "fixed",
        FixedSearchConfig(**protocol["fixed_search"]),
        binding=ledger_metadata["binding"],
        resume=True,
    )
    trials, baseline = fixed_tables(root, out, replays)
    for path in sorted(root.glob("controller-calibration-*/matrix.json")):
        matrix = json.loads(path.read_text())
        for cell in matrix["runs"]:
            restored = path.parent / Path(cell["run_path"]).name
            if digest(restored / "run.json") != cell["run_sha256"]:
                raise ValueError("Restored controller-calibration report hash differs")
            verify_run(
                restored, json.loads((restored / "run.json").read_text()), replays[cell["target"]]
            )
    summary, daily, trajectories = comparison_tables(root, out, jobs, protocol, replays, checked)
    selected = json.loads((root / "fixed-selection.json").read_text())
    controller = json.loads((root / "controller-selection.json").read_text())
    draw_figures(out, protocol, trials, baseline, selected, summary, trajectories, daily)
    write_handoff(out, checked, selected, controller, summary)
    costs = summarize(root, jobs)
    (out / "cost-summary.json").write_text(json.dumps(costs, indent=2) + "\n")
    import matplotlib.pyplot as plt

    cost_rows = costs["comparison_by_method"]
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.bar(list(METHODS), [cost_rows[m]["known_wall_seconds"] for m in METHODS])
    ax.set(
        ylabel="Measured invocation wall (seconds)",
        title="Serial T4 evaluation cost; frozen uses exact reuse",
    )
    ax.tick_params(axis="x", rotation=15)
    fig.savefig(out / "evaluation-cost.png", dpi=180)
    fig.savefig(out / "evaluation-cost.pdf")
    plt.close(fig)
    inputs.reauthenticate()
    manifest = {
        str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": digest(p)}
        for p in sorted(out.iterdir())
        if p.is_file()
    }
    (out / "artifact-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("study", "inputs", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
