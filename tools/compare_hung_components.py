"""Bounded CPU fixture comparison against a separately supplied frozen Hung checkout.

No training data/weights are imported and no foreign implementation is integrated.
Routine CI does not download or require the other checkout.
"""

import argparse
import importlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import torch

from ev_control.confidence import ControllerConfig, DailyScore, decide
from ev_models.checkpoint import digest, write_json
from ev_models.model import ForecastGRU, ModelConfig, retention_loss

HUNG_SHA = "b1f9edaa7f5c28e081159e90bedd58765afeb1a1"
EXPECTED = {
    "model.py": "c8303d1c9e83ee4bdaf6f5ce6c3e520dc22ce95d51c442375ea8fa3e9879ef76",
    "retention.py": "a4aa9c67d5f0262de9bb81089f2788295fba93cc4a25948e5409b48b849a03f6",
    "controller.py": "42ebc1c308569e41ca404c34af1c96daff509db3f6bf4544c6b95a4cbb158c2f",
}


def compare(root: Path) -> dict:
    observed = {name: digest(root / "experiments/supporting_pipeline" / name) for name in EXPECTED}
    if observed != EXPECTED:
        raise ValueError("Foreign component bytes differ from the inspected pinned revision")
    sys.path.insert(0, str(root.resolve()))
    hm = importlib.import_module("experiments.supporting_pipeline.model")
    hr = importlib.import_module("experiments.supporting_pipeline.retention")
    hc = importlib.import_module("experiments.supporting_pipeline.controller")
    torch.set_num_threads(1)
    torch.manual_seed(123)
    own = ForecastGRU(ModelConfig(64)).eval()
    other = hm.ForecastGRU(hm.ModelConfig(calendar_hidden=8)).eval()
    other.encoder.load_state_dict(own.encoder.state_dict(), strict=True)
    x = torch.linspace(-0.5, 0.5, 2 * 24 * 7).reshape(2, 24, 7)
    calendar = torch.linspace(-1, 1, 2 * 24 * 5).reshape(2, 24, 5)
    with torch.no_grad():
        difference = (own.encode(x) - other.encode(x)).abs().max().item()
        a, b = own(x, calendar), other(x, calendar)
    if (
        difference != 0
        or a.shape != (2, 24)
        or b.shape != (2, 24)
        or (a < 0).any()
        or (b < 0).any()
    ):
        raise ValueError("Encoder/shape fixture failed")
    scale = torch.linspace(0.1, 2, 64, dtype=torch.float64)
    z = torch.linspace(-1, 1, 128, dtype=torch.float64).reshape(2, 64)
    expected = (
        sum((float(z[i, k]) / (float(scale[k]) + 0.001)) ** 2 for i in range(2) for k in range(64))
        / 128
    )
    losses = []
    gradients = []
    for lossfn in (retention_loss, hr.retention_loss):
        target = z.clone().requires_grad_()
        source = torch.zeros_like(target, requires_grad=True)
        loss = lossfn(target, source, scale, epsilon=0.001)
        loss.backward()
        if source.grad is not None:
            raise ValueError("Reference gradient leaked")
        losses.append(loss.item())
        gradients.append(target.grad)
    if any(abs(v - expected) > 1e-12 for v in losses) or not torch.equal(*gradients):
        raise ValueError("Loss/gradient fixture disagrees")
    shared = ControllerConfig(0.1, 0.2, 0.0, 14, 5, 0.0, 0.05, 2, 100, 7)
    foreign = hc.ControllerConfig(shared.levels, 0.0, 14, 5, 0.0, 0.05, 2, 100, 7, "bonferroni_two")
    start = datetime(2022, 12, 1)
    end = start + timedelta(days=14)
    cases = []
    for name, count, values, expected_level in [
        ("insufficient", 4, (2.0, 1.0, 0.0), 0.0),
        ("equal", 14, (1.0, 1.0, 1.0), 0.0),
        ("strong_challenger", 14, (3.0, 2.0, 1.0), 0.2),
        ("equal_challenger_lcb_nearest", 14, (3.0, 1.0, 1.0), 0.1),
    ]:
        rows = []
        foreign_rows = []
        for i in range(count):
            day = start + timedelta(days=i)
            rows.append(
                DailyScore(
                    day,
                    day,
                    day + timedelta(days=1),
                    24,
                    values,
                    "scale",
                    tuple(f"{i}-{j}" for j in range(3)),
                )
            )
            foreign_rows.append(hc.DailyScore(day.isoformat(), True, True, values))
        ours = decide(
            rows,
            config=shared,
            active_lambda=0.0,
            block_start=start,
            as_of=end,
            stream_id="fixture",
            scale_id="scale",
        )
        theirs = hc.decide_block(foreign, current_level=0.0, block_id=0, days=foreign_rows)
        if ours.selected_lambda != expected_level or theirs.selected_level != expected_level:
            raise ValueError("Shared constant-score controller fixture disagrees")
        cases.append({"case": name, "selected_lambda": expected_level, "result": "PASS"})
    return {
        "scope": "CPU fixture/component comparison only; no performance or full-run equivalence",
        "hung_revision": HUNG_SHA,
        "hung_files_sha256": observed,
        "torch": torch.__version__,
        "encoder_max_abs_difference": difference,
        "total_model_parameters": {
            "qyroven": sum(p.numel() for p in own.parameters()),
            "hung": sum(p.numel() for p in other.parameters()),
        },
        "head_equivalence": "Different topologies; cannot assert full forecast/checkpoint equivalence",
        "retention_expected": expected,
        "retention_actual": losses,
        "target_gradient_exact_match": True,
        "source_gradient": "None in both",
        "controller_constant_cases": cases,
        "bootstrap_equivalence": "Not established: quantile convention and RNG derivation differ",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hung-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.hung_root)
    write_json(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
