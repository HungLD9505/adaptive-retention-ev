"""Replay execution engine for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

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
    mae_kwh: float
    rmse_kwh: float
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
        """Run 90-day replay for one model instance on target data."""
        start_time = time.perf_counter()
        target_id = replay_data.entity_id
        p95_scale = replay_data.p95_scale

        seed_str = f"seed{seed}" if seed is not None else "det"
        run_id = f"cyber_{model.name.lower().replace(' ', '_').replace('-', '_')}_{mode}_{target_id}_{seed_str}"

        daily_results: list[DailyResult] = []
        scheduled_count = len(replay_data.schedule)
        issued_count = 0
        scored_count = 0

        inference_seconds = 0.0
        update_seconds = 0.0

        daily_maes: list[float] = []
        squared_errors: list[float] = []

        # Iterate chronologically through scheduled origins
        for item in replay_data.schedule:
            origin = item["origin"]
            status = item["status"]

            # 1. Prediction step
            if status == "created" and origin in replay_data.forecasts:
                fc_record = replay_data.forecasts[origin]
                t0 = time.perf_counter()
                pred_scaled = model.predict(fc_record)
                inference_seconds += time.perf_counter() - t0

                pred_kwh = [p * p95_scale for p in pred_scaled]
                issued = True
                issued_count += 1
            else:
                pred_scaled = None
                pred_kwh = None
                issued = False

            # 2. Evaluation and online update step
            lbl_record = replay_data.labels.get(origin)
            is_complete_label = False
            if lbl_record is not None:
                is_complete_label = all(lbl_record.get("file_valid", [])) and all(
                    a is not None for a in lbl_record.get("available_at", [])
                )

            scored = False
            mae_val = None
            rmse_val = None
            gt_kwh = None

            if issued and is_complete_label and lbl_record is not None:
                gt_kwh = lbl_record["energy_kwh"]
                diffs = [abs(p - y) for p, y in zip(pred_kwh, gt_kwh, strict=True)]
                sq_diffs = [(p - y) ** 2 for p, y in zip(pred_kwh, gt_kwh, strict=True)]

                mae_val = float(np.mean(diffs))
                rmse_val = float(math.sqrt(np.mean(sq_diffs)))

                daily_maes.append(mae_val)
                squared_errors.extend(sq_diffs)

                scored = True
                scored_count += 1

                # 3. Model online update on newly available complete day
                y_scaled = [y / p95_scale for y in gt_kwh]
                t0 = time.perf_counter()
                model.update(fc_record, y_scaled)
                update_seconds += time.perf_counter() - t0

            daily_results.append(
                DailyResult(
                    origin=origin,
                    issued=issued,
                    scored=scored,
                    mae_kwh=mae_val,
                    rmse_kwh=rmse_val,
                    predictions_kwh=pred_kwh,
                    ground_truth_kwh=gt_kwh,
                )
            )

        total_elapsed = time.perf_counter() - start_time + source_fit_seconds + target_adapt_seconds

        overall_mae = float(np.mean(daily_maes)) if daily_maes else 0.0
        overall_rmse = float(math.sqrt(np.mean(squared_errors))) if squared_errors else 0.0

        # Save predictions JSON artifact and compute SHA-256
        preds_export = {
            "run_id": run_id,
            "model": model.name,
            "mode": mode,
            "station_id": target_id,
            "seed": seed,
            "daily_results": [asdict(d) for d in daily_results],
        }
        preds_json = json.dumps(preds_export, indent=2)
        preds_sha256 = hashlib.sha256(preds_json.encode("utf-8")).hexdigest()

        artifact_path = self.config.output_dir / f"{run_id}_predictions.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(preds_json)

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
    """Append a RunSummary row to runs.csv."""
    header = (
        "run_id,model,mode,station_id,seed,scheduled_days,issued_days,scored_days,"
        "mae_kwh,rmse_kwh,param_count,source_fit_seconds,target_adapt_seconds,"
        "inference_seconds,update_seconds,total_seconds,predictions_sha256\n"
    )
    exists = csv_path.is_file() and csv_path.stat().st_size > 0

    with open(csv_path, "a", encoding="utf-8") as f:
        if not exists:
            f.write(header)
        seed_str = str(summary.seed) if summary.seed is not None else ""
        row = (
            f"{summary.run_id},{summary.model},{summary.mode},{summary.station_id},{seed_str},"
            f"{summary.scheduled_days},{summary.issued_days},{summary.scored_days},"
            f"{summary.mae_kwh:.6f},{summary.rmse_kwh:.6f},{summary.param_count},"
            f"{summary.source_fit_seconds:.4f},{summary.target_adapt_seconds:.4f},"
            f"{summary.inference_seconds:.4f},{summary.update_seconds:.4f},"
            f"{summary.total_seconds:.4f},{summary.predictions_sha256}\n"
        )
        f.write(row)
