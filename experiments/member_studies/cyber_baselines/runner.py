"""Replay execution engine for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from experiments.member_studies.cyber_baselines.config import (
    RUNS_CSV_PATH,
    BenchmarkConfig,
)
from experiments.member_studies.cyber_baselines.data import TargetReplayData
from experiments.member_studies.cyber_baselines.models.base import BaseForecaster


@dataclass
class DailyResult:
    """Evaluation result for one replay day."""

    origin: str
    issued: bool
    scored: bool
    mae_kwh: float | None
    rmse_kwh: float | None
    predictions_kwh: list[float] | None
    ground_truth_kwh: list[float] | None


@dataclass
class RunSummary:
    """Summary of a benchmark run for one model/mode/target/seed."""

    run_id: str
    model: str
    mode: str
    station_id: str
    seed: int | None
    scheduled_days: int
    issued_days: int
    scored_days: int
    mae_kwh: float | None
    rmse_kwh: float | None
    param_count: int
    source_fit_seconds: float
    target_adapt_seconds: float
    inference_seconds: float
    update_seconds: float
    total_seconds: float
    predictions_sha256: str


class BenchmarkRunner:
    """Executes 90-day Development replay under strict causal availability guards."""

    def __init__(self, config: BenchmarkConfig = BenchmarkConfig()) -> None:
        self.config = config
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def run_replay(
        self,
        model: BaseForecaster,
        replay_data: TargetReplayData,
        mode: str = "target_only",
        seed: int | None = None,
        source_fit_seconds: float = 0.0,
        target_adapt_seconds: float = 0.0,
    ) -> RunSummary:
        """Run 90-day replay for one model instance on target data under causal arrival gating."""
        start_time = time.perf_counter()
        target_id = replay_data.entity_id
        p95_scale = replay_data.p95_scale

        seed_str = f"seed{seed}" if seed is not None else "det"
        run_id = f"cyber_{model.name.lower().replace(' ', '_').replace('-', '_')}_{mode}_{target_id}_{seed_str}"

        scheduled_count = len(replay_data.schedule)
        issued_count = 0
        scored_count = 0

        inference_seconds = 0.0
        update_seconds = 0.0

        daily_maes: list[float] = []
        squared_errors: list[float] = []

        # Map to hold DailyResult for all scheduled origins in order
        daily_results_map: dict[str, DailyResult] = {}
        # Pending issued forecasts waiting for label arrival: list of dicts
        pending_evaluations: list[dict[str, Any]] = []

        # Chronological replay loop
        for item in replay_data.schedule:
            origin = item["origin"]
            status = item["status"]
            current_as_of = datetime.fromisoformat(origin)

            # 1. Prediction step: Predict origin before any labels arriving at or after current_as_of
            if status == "created" and origin in replay_data.forecasts:
                fc_record = replay_data.forecasts[origin]
                t0 = time.perf_counter()
                pred_scaled = model.predict(fc_record)
                inference_seconds += time.perf_counter() - t0

                pred_kwh = [p * p95_scale for p in pred_scaled]
                issued_count += 1

                pending_evaluations.append(
                    {
                        "origin": origin,
                        "fc_record": fc_record,
                        "pred_scaled": pred_scaled,
                        "pred_kwh": pred_kwh,
                    }
                )
            else:
                daily_results_map[origin] = DailyResult(
                    origin=origin,
                    issued=False,
                    scored=False,
                    mae_kwh=None,
                    rmse_kwh=None,
                    predictions_kwh=None,
                    ground_truth_kwh=None,
                )

            # 2. Causal Label Arrival & Model Update step:
            # Check pending evaluations whose labels have arrived by current_as_of
            still_pending: list[dict[str, Any]] = []
            for pending in pending_evaluations:
                p_origin = pending["origin"]
                lbl_record = replay_data.labels.get(p_origin)

                if lbl_record is None:
                    still_pending.append(pending)
                    continue

                avail_times = lbl_record.get("available_at", [])
                file_valid = lbl_record.get("file_valid", [])

                # Strict causal guard: label has arrived if all 24 hourly timestamps are <= current_as_of
                has_arrived = len(avail_times) == 24 and all(
                    a is not None and datetime.fromisoformat(a) <= current_as_of
                    for a in avail_times
                )

                if has_arrived:
                    # Check sensor validity
                    is_complete = all(file_valid)
                    if is_complete:
                        gt_kwh = lbl_record["energy_kwh"]
                        p_kwh = pending["pred_kwh"]
                        diffs = [abs(p - y) for p, y in zip(p_kwh, gt_kwh, strict=True)]
                        sq_diffs = [(p - y) ** 2 for p, y in zip(p_kwh, gt_kwh, strict=True)]

                        mae_val = float(np.mean(diffs))
                        rmse_val = float(math.sqrt(np.mean(sq_diffs)))

                        daily_maes.append(mae_val)
                        squared_errors.extend(sq_diffs)
                        scored_count += 1

                        daily_results_map[p_origin] = DailyResult(
                            origin=p_origin,
                            issued=True,
                            scored=True,
                            mae_kwh=mae_val,
                            rmse_kwh=rmse_val,
                            predictions_kwh=p_kwh,
                            ground_truth_kwh=gt_kwh,
                        )

                        # Model online update on arrived ground truth
                        y_scaled = [y / p95_scale for y in gt_kwh]
                        t0 = time.perf_counter()
                        model.update(pending["fc_record"], y_scaled)
                        update_seconds += time.perf_counter() - t0
                    else:
                        # Arrived but incomplete sensors (dropout null) -> cannot be scored
                        daily_results_map[p_origin] = DailyResult(
                            origin=p_origin,
                            issued=True,
                            scored=False,
                            mae_kwh=None,
                            rmse_kwh=None,
                            predictions_kwh=pending["pred_kwh"],
                            ground_truth_kwh=None,
                        )
                else:
                    still_pending.append(pending)

            pending_evaluations = still_pending

        # 3. Post-Replay Evaluation of Final Horizon:
        # After replay ends, clock advances past the final forecast horizon
        if pending_evaluations:
            final_as_of = datetime.fromisoformat(replay_data.schedule[-1]["origin"]) + timedelta(
                days=1
            )
            for pending in pending_evaluations:
                p_origin = pending["origin"]
                lbl_record = replay_data.labels.get(p_origin)
                if lbl_record is not None:
                    avail_times = lbl_record.get("available_at", [])
                    file_valid = lbl_record.get("file_valid", [])
                    has_arrived = len(avail_times) == 24 and all(
                        a is not None and datetime.fromisoformat(a) <= final_as_of
                        for a in avail_times
                    )
                    if has_arrived and all(file_valid):
                        gt_kwh = lbl_record["energy_kwh"]
                        p_kwh = pending["pred_kwh"]
                        diffs = [abs(p - y) for p, y in zip(p_kwh, gt_kwh, strict=True)]
                        sq_diffs = [(p - y) ** 2 for p, y in zip(p_kwh, gt_kwh, strict=True)]

                        mae_val = float(np.mean(diffs))
                        rmse_val = float(math.sqrt(np.mean(sq_diffs)))

                        daily_maes.append(mae_val)
                        squared_errors.extend(sq_diffs)
                        scored_count += 1

                        daily_results_map[p_origin] = DailyResult(
                            origin=p_origin,
                            issued=True,
                            scored=True,
                            mae_kwh=mae_val,
                            rmse_kwh=rmse_val,
                            predictions_kwh=p_kwh,
                            ground_truth_kwh=gt_kwh,
                        )
                    else:
                        daily_results_map[p_origin] = DailyResult(
                            origin=p_origin,
                            issued=True,
                            scored=False,
                            mae_kwh=None,
                            rmse_kwh=None,
                            predictions_kwh=pending["pred_kwh"],
                            ground_truth_kwh=None,
                        )
                else:
                    daily_results_map[p_origin] = DailyResult(
                        origin=p_origin,
                        issued=True,
                        scored=False,
                        mae_kwh=None,
                        rmse_kwh=None,
                        predictions_kwh=pending["pred_kwh"],
                        ground_truth_kwh=None,
                    )

        # Assemble daily results in exact schedule order
        ordered_daily_results = [daily_results_map[item["origin"]] for item in replay_data.schedule]

        total_elapsed = time.perf_counter() - start_time + source_fit_seconds + target_adapt_seconds

        # Exact null-accounting for unscored / zero-score runs
        if scored_count > 0:
            overall_mae: float | None = float(np.mean(daily_maes))
            overall_rmse: float | None = float(math.sqrt(np.mean(squared_errors)))
        else:
            overall_mae = None
            overall_rmse = None

        # Build predictions export dictionary
        preds_export: dict[str, Any] = {
            "run_id": run_id,
            "model": model.name,
            "mode": mode,
            "station_id": target_id,
            "seed": seed,
            "scheduled_days": scheduled_count,
            "issued_days": issued_count,
            "scored_days": scored_count,
            "mae_kwh": overall_mae,
            "rmse_kwh": overall_rmse,
            "daily_results": [asdict(d) for d in ordered_daily_results],
        }
        if scored_count == 0:
            preds_export["unscored_reason"] = "zero_scored_observations"

        # Byte-level LF serialization policy: binary mode prevents Windows CRLF translation
        preds_json = json.dumps(preds_export, indent=2)
        preds_bytes = preds_json.encode("utf-8")
        preds_sha256 = hashlib.sha256(preds_bytes).hexdigest()

        artifact_path = self.config.output_dir / f"{run_id}_predictions.json"
        with open(artifact_path, "wb") as f:
            f.write(preds_bytes)

        return RunSummary(
            run_id=run_id,
            model=model.name,
            mode=mode,
            station_id=target_id,
            seed=seed,
            scheduled_days=scheduled_count,
            issued_days=issued_count,
            scored_days=scored_count,
            mae_kwh=overall_mae,
            rmse_kwh=overall_rmse,
            param_count=model.param_count,
            source_fit_seconds=source_fit_seconds,
            target_adapt_seconds=target_adapt_seconds,
            inference_seconds=inference_seconds,
            update_seconds=update_seconds,
            total_seconds=total_elapsed,
            predictions_sha256=preds_sha256,
        )


def append_summary_to_csv(summary: RunSummary, csv_path: Path = RUNS_CSV_PATH) -> None:
    """Append a RunSummary row to runs.csv with explicit LF newline policy."""
    header = (
        "run_id,model,mode,station_id,seed,scheduled_days,issued_days,scored_days,"
        "mae_kwh,rmse_kwh,param_count,source_fit_seconds,target_adapt_seconds,"
        "inference_seconds,update_seconds,total_seconds,predictions_sha256\n"
    )
    exists = csv_path.is_file() and csv_path.stat().st_size > 0

    with open(csv_path, "a", encoding="utf-8", newline="\n") as f:
        if not exists:
            f.write(header)
        seed_str = str(summary.seed) if summary.seed is not None else ""
        mae_str = f"{summary.mae_kwh:.6f}" if summary.mae_kwh is not None else ""
        rmse_str = f"{summary.rmse_kwh:.6f}" if summary.rmse_kwh is not None else ""
        row = (
            f"{summary.run_id},{summary.model},{summary.mode},{summary.station_id},{seed_str},"
            f"{summary.scheduled_days},{summary.issued_days},{summary.scored_days},"
            f"{mae_str},{rmse_str},{summary.param_count},"
            f"{summary.source_fit_seconds:.4f},{summary.target_adapt_seconds:.4f},"
            f"{summary.inference_seconds:.4f},{summary.update_seconds:.4f},"
            f"{summary.total_seconds:.4f},{summary.predictions_sha256}\n"
        )
        f.write(row)
