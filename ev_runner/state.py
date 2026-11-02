"""Independent model/optimizer/RNG branches and content identity helpers."""

import copy
import hashlib
import io
import json
import random

import torch

from ev_models.model import ForecastGRU, ModelConfig
from ev_models.training import TrainingConfig, train_epoch


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def rng_state() -> dict:
    return {
        "cpu": torch.get_rng_state().clone(),
        "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
        "python": random.getstate(),
    }


def restore_rng(value: dict) -> None:
    torch.set_rng_state(value["cpu"])
    random.setstate(value["python"])
    if value["cuda"]:
        if not torch.cuda.is_available() or len(value["cuda"]) != torch.cuda.device_count():
            raise ValueError("Exact replay requires identical CUDA topology")
        torch.cuda.set_rng_state_all(value["cuda"])


class Branch:
    """No shared mutable model/optimizer/RNG; restore RNG before each operation."""

    def __init__(self, model: ForecastGRU, optimizer: torch.optim.Optimizer, rng: dict) -> None:
        self.model, self.optimizer, self.rng = model, optimizer, copy.deepcopy(rng)
        self.steps = 0

    def snapshot(self) -> dict:
        return copy.deepcopy(
            {
                "model": self.model.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "rng": self.rng,
                "steps": self.steps,
                "architecture": self.model.architecture(),
            }
        )

    @classmethod
    def from_snapshot(cls, value: dict, *, device: str, learning_rate: float) -> "Branch":
        # Construction consumes global RNG, but each branch operation restores its own.
        model = ForecastGRU(ModelConfig(value["architecture"]["head_width"])).to(device)
        model.load_state_dict(value["model"])
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        optimizer.load_state_dict(value["optimizer"])
        branch = cls(model, optimizer, value["rng"])
        branch.steps = value["steps"]
        return branch

    def clone(self, *, device: str, learning_rate: float) -> "Branch":
        return self.from_snapshot(self.snapshot(), device=device, learning_rate=learning_rate)

    def predict(self, record: dict, *, device: str) -> list[float]:
        restore_rng(self.rng)
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(
                torch.tensor([record["x_hist"]], dtype=torch.float32, device=device),
                torch.tensor([record["c_future"]], dtype=torch.float32, device=device),
            )[0]
        if not torch.isfinite(prediction).all():
            raise ValueError("Nonfinite saved forecast")
        self.rng = rng_state()
        return prediction.cpu().tolist()

    def update(
        self,
        record: dict,
        *,
        weight: float,
        config: TrainingConfig,
        device: str,
        reference: ForecastGRU | None,
        latent_scale: torch.Tensor | None,
        event_index: int,
    ) -> list[dict]:
        restore_rng(self.rng)
        logs = []
        for epoch in range(config.epochs):
            log = train_epoch(
                self.model,
                self.optimizer,
                [record],
                config,
                epoch=event_index * config.epochs + epoch,
                device=device,
                reference=reference,
                latent_scale=latent_scale,
                retention_weight=weight,
            )
            self.steps += log["steps"]
            logs.append(log)
        self.rng = rng_state()
        return logs


def state_digest(value: object) -> str:
    """Stable recursive tensor/value digest; avoid nondeterministic pickle storage IDs."""
    result = hashlib.sha256()

    def visit(x):
        if isinstance(x, torch.Tensor):
            t = x.detach().cpu().contiguous()
            result.update(canonical([str(t.dtype), list(t.shape)]))
            result.update(t.numpy().tobytes())
        elif isinstance(x, dict):
            for k in sorted(x, key=lambda k: (type(k).__name__, str(k))):
                visit(k)
                visit(x[k])
        elif isinstance(x, (tuple, list)):
            result.update(canonical([type(x).__name__, len(x)]))
            for part in x:
                visit(part)
        else:
            result.update(canonical(x))

    visit(value)
    return result.hexdigest()


def torch_bytes(value: object) -> bytes:
    stream = io.BytesIO()
    torch.save(value, stream)
    return stream.getvalue()
