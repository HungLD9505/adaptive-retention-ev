"""Study Runner for the Independent Confidence-Controller Training Study.

Follows Issue #41 & Report 1:
1. Trains a bounded Source GRU checkpoint on source samples, extracts s_k latent scales.
2. Performs Target Adaptation and Chronological Replay across 14-day block boundaries.
3. Evaluates 7-day, 14-day, and 28-day initial history budgets on Development targets.
4. Adheres strictly to prequential order:
   - Forecast issued and recorded before labels arrive.
   - Complete 24-hour label arrival verified.
   - Prequential scoring (daily normalized MAE).
   - Candidate parameter updates with paired randomness.
   - Block decision via day-block bootstrap LCB > delta.
   - Winning candidate's trained model and optimizer carried forward.
5. Records execution metrics, runtime, update cost, and artifact SHA-256 hashes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import time
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.optim as optim

from ev_runner.replay import Replay
from experiments.confidence_controller.controller import (
    AdaptiveRetentionController,
)
from experiments.confidence_controller.model import (
    EVForecasterGRU,
    LatentRetentionLoss,
    compute_forecast_mae,
)

from .study_data import load_initial_target_samples

LOGGER = logging.getLogger("cyber_controller_runner")


def sha256_bytes(data: bytes) -> str:
    """Return SHA-256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TargetCandidate:
    """Represents one of the 3 candidates in an active evaluation block."""

    def __init__(
        self,
        candidate_id: str,
        lambda_val: float,
        model: EVForecasterGRU,
        optimizer: optim.Optimizer,
        retention_loss_fn: LatentRetentionLoss,
        device: torch.device,
    ) -> None:
        self.candidate_id = candidate_id
        self.lambda_val = lambda_val
        self.model = model
        self.optimizer = optimizer
        self.retention_loss_fn = retention_loss_fn
        self.device = device
        self.update_steps_count = 0

    def predict(self, x_hist: torch.Tensor, c_future: torch.Tensor) -> np.ndarray:
        """Issue 24h predictions without computing gradients."""
        self.model.eval()
        with torch.no_grad():
            x_t = x_hist.to(self.device)
            c_t = c_future.to(self.device)
            y_hat, _ = self.model(x_t, c_t)
            return y_hat.cpu().numpy()[0]

    def update_on_day(
        self,
        x_hist: torch.Tensor,
        c_future: torch.Tensor,
        y_scaled: torch.Tensor,
    ) -> float:
        """Perform 1 gradient update step on the arrived daily label."""
        self.model.train()
        self.optimizer.zero_grad()

        x_t = x_hist.to(self.device)
        c_t = c_future.to(self.device)
        y_t = y_scaled.to(self.device)

        y_hat, z_target = self.model(x_t, c_t)
        loss_forecast = compute_forecast_mae(y_hat, y_t).mean()

        if self.lambda_val > 0.0:
            loss_retain = self.retention_loss_fn(z_target, x_t)
            total_loss = loss_forecast + self.lambda_val * loss_retain
        else:
            total_loss = loss_forecast

        total_loss.backward()
        self.optimizer.step()
        self.update_steps_count += 1
        return float(total_loss.item())


def pretrain_source_model(
    x_source: torch.Tensor,
    c_source: torch.Tensor,
    y_source: torch.Tensor,
    epochs: int = 10,
    batch_size: int = 32,
    lr: float = 1e-3,
    device: torch.device = torch.device("cpu"),
    seed: int = 42,
) -> Tuple[EVForecasterGRU, torch.Tensor]:
    """Train bounded source GRU model and compute latent dimension standard deviation s_k."""
    torch.manual_seed(seed)
    model = EVForecasterGRU().to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    n_samples = x_source.size(0)
    dataset = torch.utils.data.TensorDataset(x_source, c_source, y_source)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    LOGGER.info("Starting bounded Source Pretraining: %d samples, %d epochs", n_samples, epochs)
    model.train()
    for ep in range(epochs):
        total_loss = 0.0
        for bx, bc, by in loader:
            bx, bc, by = bx.to(device), bc.to(device), by.to(device)
            optimizer.zero_grad()
            y_hat, _ = model(bx, bc)
            loss = compute_forecast_mae(y_hat, by).mean()
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(bx)
        LOGGER.debug("Source Epoch %d/%d - Loss: %.5f", ep + 1, epochs, total_loss / n_samples)

    # Compute latent standard deviations s_k across all source samples
    model.eval()
    with torch.no_grad():
        all_z = []
        for i in range(0, n_samples, batch_size):
            bx = x_source[i : i + batch_size].to(device)
            z = model.encoder(bx)
            all_z.append(z.cpu())
        z_tensor = torch.cat(all_z, dim=0)  # [n_samples, 64]
        s_k = torch.std(z_tensor, dim=0)  # [64]
        # Replace zero or near-zero variance with small fallback
        s_k = torch.clamp(s_k, min=1e-3)

    LOGGER.info(
        "Source pretraining complete. Latent s_k mean: %.4f, min: %.4f, max: %.4f",
        s_k.mean().item(),
        s_k.min().item(),
        s_k.max().item(),
    )
    return model, s_k


def run_target_replay_study(
    source_model: EVForecasterGRU,
    s_k: torch.Tensor,
    stream: Replay,
    history_days: int,
    entity_id: List[str],
    forecast_path: Path,
    block_size: int = 14,
    lambda_low: float = 0.1,
    lambda_high: float = 1.0,
    initial_lambda: float = 0.1,
    b_min: int = 10,
    delta: float = 0.0,
    alpha: float = 0.05,
    seed: int = 42,
    device: torch.device = torch.device("cpu"),
) -> Dict[str, Any]:
    """Execute prequential forecast-score-update replay across blocks."""
    total_stream_days = (stream.stop - stream.start).days
    if block_size < 1 or total_stream_days < 1 or total_stream_days % block_size:
        raise ValueError("Study requires complete calendar blocks; partial blocks unsupported")
    if stream.delay != timedelta(0):
        raise ValueError(
            "Study supports zero configured label delay; use the primary runner otherwise"
        )
    num_blocks = total_stream_days // block_size
    if forecast_path.exists():
        raise FileExistsError(forecast_path)
    if not np.isfinite(stream.scale) or stream.scale <= 0:
        raise ValueError("A finite positive authenticated scale is required")

    # Build frozen source encoder
    source_encoder = copy.deepcopy(source_model.encoder)
    retention_loss_fn = LatentRetentionLoss(source_encoder=source_encoder, s_k=s_k.to(device)).to(
        device
    )

    # Initialize active target model from source checkpoint
    active_model = copy.deepcopy(source_model).to(device)
    active_optimizer = optim.Adam(active_model.parameters(), lr=1e-3)

    # Initial target adaptation on permitted historical prefix samples (if present)
    if stream.inputs is not None:
        x_init, c_init, y_init = load_initial_target_samples(stream.inputs, entity_id=entity_id)
        if len(x_init) > 0:
            LOGGER.info(
                "Initial adaptation on %d prefix samples for %s (5 epochs, lambda=%.2f)",
                len(x_init),
                entity_id,
                initial_lambda,
            )
            active_model.train()
            init_dataset = torch.utils.data.TensorDataset(x_init, c_init, y_init)
            init_loader = torch.utils.data.DataLoader(
                init_dataset, batch_size=min(16, len(x_init)), shuffle=True
            )
            for _ in range(5):
                for bx, bc, by in init_loader:
                    bx, bc, by = bx.to(device), bc.to(device), by.to(device)
                    active_optimizer.zero_grad()
                    y_hat, z_target = active_model(bx, bc)
                    loss_fc = compute_forecast_mae(y_hat, by).mean()
                    if initial_lambda > 0.0:
                        loss_ret = retention_loss_fn(z_target, bx)
                        tot_loss = loss_fc + initial_lambda * loss_ret
                    else:
                        tot_loss = loss_fc
                    tot_loss.backward()
                    active_optimizer.step()

    controller = AdaptiveRetentionController(
        lambda_low=lambda_low,
        lambda_high=lambda_high,
        initial_lambda=initial_lambda,
        block_size=block_size,
        b_min=b_min,
        delta=delta,
        alpha=alpha,
        seed=seed,
    )

    LOGGER.info(
        "Running target replay for %s (%d days history budget): %d days stream, %d blocks of %d days",
        entity_id,
        history_days,
        total_stream_days,
        num_blocks,
        block_size,
    )

    all_daily_records: List[Dict[str, Any]] = []
    block_decisions: List[Dict[str, Any]] = []
    total_inference_time = 0.0
    total_training_time = 0.0
    total_update_steps = 0

    day_pointer = 0
    with forecast_path.open("x", encoding="utf-8") as forecast_log:
        for blk_idx in range(num_blocks):
            # 1. At start of block: clone active model and optimizer into all 3 candidates
            candidates: Dict[str, TargetCandidate] = {}
            candidate_configs = controller.get_candidate_configs()

            for cfg in candidate_configs:
                # Deepcopy active model and optimizer state into each candidate
                c_model = copy.deepcopy(active_model).to(device)
                c_opt = optim.Adam(c_model.parameters(), lr=1e-3)
                c_opt.load_state_dict(copy.deepcopy(active_optimizer.state_dict()))
                candidates[cfg.candidate_id] = TargetCandidate(
                    candidate_id=cfg.candidate_id,
                    lambda_val=cfg.lambda_val,
                    model=c_model,
                    optimizer=c_opt,
                    retention_loss_fn=retention_loss_fn,
                    device=device,
                )

            LOGGER.info(
                "--- Block %d Start: Active=%s (lambda=%.2f) ---",
                blk_idx,
                controller.active_id,
                controller.active_lambda,
            )

            # 2. Iterate through days of the block
            for day_in_blk in range(block_size):
                origin = stream.start + timedelta(days=day_pointer)
                day_data = stream.forecast(origin)
                if day_data is None:
                    controller.record_day_scores(day_pointer, False, {})
                    all_daily_records.append(
                        {
                            "day_index": day_pointer,
                            "origin": origin.isoformat(),
                            "status": "no_forecast",
                        }
                    )
                    day_pointer += 1
                    continue
                x_tensor = torch.tensor([day_data["x_hist"]], dtype=torch.float32)
                c_tensor = torch.tensor([day_data["c_future"]], dtype=torch.float32)
                t_inf_start = time.perf_counter()
                preds = {cid: cand.predict(x_tensor, c_tensor) for cid, cand in candidates.items()}
                total_inference_time += time.perf_counter() - t_inf_start
                if any(p.shape != (24,) or not np.isfinite(p).all() for p in preds.values()):
                    raise ValueError("Invalid issued forecast")
                forecast_log.write(
                    json.dumps(
                        {
                            "origin": origin.isoformat(),
                            "active_id": controller.active_id,
                            "energy_scale": stream.scale,
                            "predictions_scaled": {cid: p.tolist() for cid, p in preds.items()},
                        },
                        allow_nan=False,
                    )
                    + "\n"
                )
                forecast_log.flush()
                os.fsync(forecast_log.fileno())

                # PREQUENTIAL STEP 2 & 3: LABEL ARRIVES & SCORE
                outcome = stream.labels(origin, origin + timedelta(days=1))
                if outcome.status == "pending":
                    raise ValueError("Label is not yet available at the study daily update clock")
                if outcome.status not in {"complete", "incomplete"}:
                    raise ValueError("Unknown label outcome")
                is_valid = outcome.status == "complete"
                maes: Dict[str, float] = {}
                if is_valid:
                    y_true = np.array(outcome.values, dtype=np.float32) / stream.scale
                    if y_true.shape != (24,) or not np.isfinite(y_true).all() or (y_true < 0).any():
                        raise ValueError("Invalid arrived complete label vector")
                    for cid, p in preds.items():
                        maes[cid] = float(np.mean(np.abs(p - y_true)))

                controller.record_day_scores(
                    day_index=day_pointer,
                    is_valid_day=is_valid,
                    candidate_maes=maes,
                )

                # PREQUENTIAL STEP 4: UPDATE CANDIDATES WITH ARRIVED LABELS
                if is_valid:
                    t_train_start = time.perf_counter()
                    y_tensor = torch.tensor(y_true[None, :], dtype=torch.float32)
                    for cand in candidates.values():
                        cand.update_on_day(x_tensor, c_tensor, y_tensor)
                        total_update_steps += 1
                    total_training_time += time.perf_counter() - t_train_start

                all_daily_records.append(
                    {
                        "block_index": blk_idx,
                        "day_index": day_pointer,
                        "origin": origin.isoformat(),
                        "active_id": controller.active_id,
                        "is_valid": is_valid,
                        "maes": maes,
                    }
                )
                day_pointer += 1

            # 3. End of Block: evaluate decision
            decision = controller.evaluate_block_decision(block_index=blk_idx)
            block_decisions.append(asdict(decision))

            LOGGER.info(
                "--- Block %d End: Decision=%s -> Selected=%s (lambda=%.2f), Reason: %s ---",
                blk_idx,
                decision.decision_type,
                decision.selected_id,
                decision.selected_lambda,
                decision.selection_reason,
            )

            # 4. Carry forward winning candidate's trained model and optimizer
            winning_candidate = candidates[decision.selected_id]
            active_model = copy.deepcopy(winning_candidate.model)
            active_optimizer = optim.Adam(active_model.parameters(), lr=1e-3)
            active_optimizer.load_state_dict(
                copy.deepcopy(winning_candidate.optimizer.state_dict())
            )

    return {
        "entity_id": entity_id,
        "history_days": history_days,
        "total_stream_days": total_stream_days,
        "blocks_evaluated": num_blocks,
        "block_decisions": block_decisions,
        "daily_records_count": len(all_daily_records),
        "daily_records": all_daily_records,
        "forecast_file": str(forecast_path),
        "forecast_sha256": sha256_file(forecast_path),
        "runtime_metrics": {
            "total_inference_time_sec": total_inference_time,
            "total_training_time_sec": total_training_time,
            "total_update_steps": total_update_steps,
            "candidates_per_block": 3,
        },
    }


if __name__ == "__main__":
    from .cli import main

    main()
