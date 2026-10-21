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

import argparse
import copy
import hashlib
import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.optim as optim

from experiments.member_studies.cyber_controller.controller import (
    AdaptiveRetentionController,
)
from experiments.member_studies.cyber_controller.model import (
    EVForecasterGRU,
    LatentRetentionLoss,
    compute_forecast_mae,
)

LOGGER = logging.getLogger("cyber_controller_runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


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
        lr: float = 1e-3,
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


def load_source_training_samples(
    input_dir: Path, max_samples: int = 500
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Load bounded source training samples from training.jsonl."""
    training_file = input_dir / "training.jsonl"
    x_list, c_list, y_list = [], [], []

    with training_file.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("role") == "source":
                fc = rec["forecast"]
                x_list.append(fc["x_hist"])
                c_list.append(fc["c_future"])
                y_list.append(rec["y_scaled"])
                if len(x_list) >= max_samples:
                    break

    x_tensor = torch.tensor(x_list, dtype=torch.float32)
    c_tensor = torch.tensor(c_list, dtype=torch.float32)
    y_tensor = torch.tensor(y_list, dtype=torch.float32)
    return x_tensor, c_tensor, y_tensor


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


def load_development_stream(input_dir: Path, entity_id: List[str]) -> List[Dict[str, Any]]:
    """Load chronologically aligned forecasts and labels for the specified target entity."""
    forecasts_file = input_dir / "forecasts.jsonl"
    labels_file = input_dir / "labels.jsonl"

    forecasts_by_origin: Dict[str, Dict[str, Any]] = {}
    with forecasts_file.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("identity") == entity_id:
                forecasts_by_origin[rec["origin"]] = rec

    stream: List[Dict[str, Any]] = []
    with labels_file.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("identity") == entity_id:
                origin = rec["origin"]
                if origin in forecasts_by_origin:
                    fc = forecasts_by_origin[origin]
                    # Check completeness of labels (24 non-negative finite hourly values)
                    raw_energy = rec.get("energy_kwh", [])
                    scale = fc.get("energy_scale", 1.0)
                    is_complete = bool(
                        len(raw_energy) == 24
                        and all(v is not None and not np.isnan(v) for v in raw_energy)
                        and scale is not None
                        and scale > 0
                    )
                    scaled_y = [v / scale for v in raw_energy] if is_complete else []

                    stream.append(
                        {
                            "origin": origin,
                            "x_hist": fc["x_hist"],
                            "c_future": fc["c_future"],
                            "energy_scale": scale,
                            "is_complete": is_complete,
                            "y_scaled": scaled_y,
                            "y_kwh": raw_energy,
                        }
                    )

    # Sort chronologically by origin timestamp
    stream.sort(key=lambda item: item["origin"])
    return stream


def run_target_replay_study(
    source_model: EVForecasterGRU,
    s_k: torch.Tensor,
    stream: List[Dict[str, Any]],
    history_days: int,
    entity_id: List[str],
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
    # Build frozen source encoder
    source_encoder = copy.deepcopy(source_model.encoder)
    retention_loss_fn = LatentRetentionLoss(source_encoder=source_encoder, s_k=s_k.to(device)).to(
        device
    )

    # Initialize active target model from source checkpoint
    active_model = copy.deepcopy(source_model).to(device)
    active_optimizer = optim.Adam(active_model.parameters(), lr=1e-3)

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

    total_stream_days = len(stream)
    num_blocks = total_stream_days // block_size
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
            day_data = stream[day_pointer]
            x_tensor = torch.tensor([day_data["x_hist"]], dtype=torch.float32)
            c_tensor = torch.tensor([day_data["c_future"]], dtype=torch.float32)

            # PREQUENTIAL STEP 1: FORECAST BEFORE LABELS ARRIVE
            t_inf_start = time.perf_counter()
            preds: Dict[str, np.ndarray] = {}
            for cid, cand in candidates.items():
                preds[cid] = cand.predict(x_tensor, c_tensor)
            total_inference_time += time.perf_counter() - t_inf_start

            # PREQUENTIAL STEP 2 & 3: LABEL ARRIVES & SCORE
            is_valid = day_data["is_complete"]
            maes: Dict[str, float] = {}
            if is_valid:
                y_true = np.array(day_data["y_scaled"], dtype=np.float32)
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
                y_tensor = torch.tensor([day_data["y_scaled"]], dtype=torch.float32)
                for cand in candidates.values():
                    cand.update_on_day(x_tensor, c_tensor, y_tensor)
                    total_update_steps += 1
                total_training_time += time.perf_counter() - t_train_start

            all_daily_records.append(
                {
                    "block_index": blk_idx,
                    "day_index": day_pointer,
                    "origin": day_data["origin"],
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
        active_optimizer.load_state_dict(copy.deepcopy(winning_candidate.optimizer.state_dict()))

    return {
        "entity_id": entity_id,
        "history_days": history_days,
        "total_stream_days": total_stream_days,
        "blocks_evaluated": num_blocks,
        "block_decisions": block_decisions,
        "daily_records_count": len(all_daily_records),
        "runtime_metrics": {
            "total_inference_time_sec": total_inference_time,
            "total_training_time_sec": total_training_time,
            "total_update_steps": total_update_steps,
            "candidates_per_block": 3,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Cyber Controller Training & Replay Study.")
    parser.add_argument(
        "--history-budgets",
        nargs="+",
        type=int,
        default=[7, 14, 28],
        help="Initial history budgets to evaluate (e.g. 7 14 28).",
    )
    parser.add_argument(
        "--source-samples",
        type=int,
        default=300,
        help="Number of source samples for bounded pretraining.",
    )
    parser.add_argument(
        "--source-epochs", type=int, default=5, help="Number of epochs for source pretraining."
    )
    parser.add_argument("--block-size", type=int, default=14, help="Block size in days.")
    parser.add_argument(
        "--b-min", type=int, default=10, help="Minimum complete days for block switch."
    )
    parser.add_argument("--delta", type=float, default=0.0, help="Strict improvement threshold.")
    parser.add_argument(
        "--lambda-low", type=float, default=0.1, help="Lower positive retention level."
    )
    parser.add_argument("--lambda-high", type=float, default=1.0, help="Higher retention level.")
    parser.add_argument(
        "--initial-lambda", type=float, default=0.1, help="Initial retention level."
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--output-json",
        type=str,
        default="runs/cyber_controller_study_results.json",
        help="Path to save output JSON.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    inputs_base = repo_root / "data/inputs/issue18-input-handoff-v1-20261019"
    out_path = repo_root / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    LOGGER.info("Using compute device: %s", device)

    # 1. Bounded Source Pretraining (using 14d source samples)
    source_input_dir = inputs_base / "urbanev-SZH-14d"
    x_src, c_src, y_src = load_source_training_samples(
        source_input_dir, max_samples=args.source_samples
    )
    source_model, s_k = pretrain_source_model(
        x_src, c_src, y_src, epochs=args.source_epochs, device=device, seed=args.seed
    )

    # Save bounded source checkpoint locally
    ckpt_dir = repo_root / "experiments/member_studies/cyber_controller/checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    source_ckpt_path = ckpt_dir / "source_bounded_model.pt"
    s_k_path = ckpt_dir / "latent_scale_sk.pt"
    torch.save(source_model.state_dict(), source_ckpt_path)
    torch.save(s_k, s_k_path)

    source_ckpt_hash = sha256_file(source_ckpt_path)
    s_k_hash = sha256_file(s_k_path)
    LOGGER.info("Saved Source Checkpoint SHA256: %s", source_ckpt_hash)
    LOGGER.info("Saved Latent Scale s_k SHA256: %s", s_k_hash)

    # 2. Replay Development Targets across 7d, 14d, 28d
    target_entity = ["urbanev", "SZH", "1001"]
    budget_results = {}

    for budget in args.history_budgets:
        target_dir = inputs_base / f"urbanev-SZH-{budget}d"
        stream = load_development_stream(target_dir, entity_id=target_entity)
        if not stream:
            LOGGER.warning("No stream found for budget %dd entity %s", budget, target_entity)
            continue

        res = run_target_replay_study(
            source_model=source_model,
            s_k=s_k,
            stream=stream,
            history_days=budget,
            entity_id=target_entity,
            block_size=args.block_size,
            lambda_low=args.lambda_low,
            lambda_high=args.lambda_high,
            initial_lambda=args.initial_lambda,
            b_min=args.b_min,
            delta=args.delta,
            seed=args.seed,
            device=device,
        )
        budget_results[f"{budget}d"] = res

    final_payload = {
        "study_name": "independent_cyber_controller_study",
        "issue": 41,
        "owner": "hung00cyber",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": vars(args),
        "source_checkpoint": {
            "path": str(source_ckpt_path.relative_to(repo_root)),
            "sha256": source_ckpt_hash,
            "samples": len(x_src),
            "epochs": args.source_epochs,
        },
        "latent_scale_sk": {
            "path": str(s_k_path.relative_to(repo_root)),
            "sha256": s_k_hash,
            "dim": len(s_k),
        },
        "budgets": budget_results,
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2)

    LOGGER.info("Study execution successfully completed! Results saved to %s", out_path)
    LOGGER.info("Result file SHA256: %s", sha256_file(out_path))


if __name__ == "__main__":
    main()
