"""Read verified prepared inputs; never select entities from replay outcomes."""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import torch

from ev_inputs.windows import LabelRecord, ready_labels

# Extracted only after verifying the released ZIP SHA-256 (see README).
RELEASE_MANIFESTS = {
    7: "fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c",
    14: "66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9",
    28: "cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd",
}


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def rows(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def verified_manifest(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text())
    if sha256(root / "manifest.json") != RELEASE_MANIFESTS.get(manifest["config"]["history_days"]):
        raise ValueError("Manifest is not from the pinned DATA-v1-20261019 release")
    if (manifest["schema"], manifest["feature_schema"], manifest["missing_data_policy"]) != (
        "ev-loader-run-v2",
        "ev-input-v1",
        "ev-missing-data-v1",
    ):
        raise ValueError("Unsupported prepared input contract")
    if (manifest["config"]["dataset_id"], manifest["config"]["city_id"]) != ("urbanev", "SZH"):
        raise ValueError("This bounded study is UrbanEV/SZH only")
    for name in (
        "entities.jsonl",
        "training.jsonl",
        "forecasts.jsonl",
        "labels.jsonl",
        "schedule.jsonl",
    ):
        record = manifest["files"][name]
        path = root / name
        if path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"Input fingerprint mismatch: {name}")
    return manifest


def select_entities(root: Path, source_count: int, target_count: int) -> tuple[list, list]:
    inventory = sorted(rows(root / "entities.jsonl"), key=lambda r: r["identity"])
    source = [r for r in inventory if r["role"] == "source" and r["initial_trainable"] > 0][
        :source_count
    ]
    development = [r for r in inventory if r["role"] == "development"]
    targets = [r for r in development if r["initialization"] == "target_initial_adaptation"][
        :target_count
    ]
    for mode in ("source_checkpoint_only", "blocked_undefined_scale"):
        targets += [r for r in development if r["initialization"] == mode][:1]
    if not source or not targets:
        raise ValueError("Empty permitted cohort")
    return source, targets


def training_rows(root: Path, entities: list[dict]) -> list[dict]:
    selected = {tuple(e["identity"]): e for e in entities}
    result = []
    for row in rows(root / "training.jsonl"):
        f = row["forecast"]
        entity = selected.get(tuple(f["identity"]))
        if entity is None:
            continue
        if row["role"] != entity["role"] or row["role"] not in ("source", "development"):
            raise ValueError("Role/entity mismatch")
        start, cutoff = map(datetime.fromisoformat, (entity["fit_start"], entity["cutoff"]))
        if (
            datetime.fromisoformat(f["history_labels"][0]) < start
            or datetime.fromisoformat(f["origin"]) + timedelta(days=1) > cutoff
        ):
            raise ValueError("Training example outside permitted prefix")
        if f["scale_id"] != entity["scale"]["fit_sha256"]:
            raise ValueError("Training scaler mismatch")
        result.append(row)
    for key, entity in selected.items():
        if (
            sum(tuple(r["forecast"]["identity"]) == key for r in result)
            != entity["initial_trainable"]
        ):
            raise ValueError("Training count mismatch")
    return result


def tensors(examples: list[dict]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    x = torch.tensor([r["forecast"]["x_hist"] for r in examples], dtype=torch.float32)
    c = torch.tensor([r["forecast"]["c_future"] for r in examples], dtype=torch.float32)
    y = torch.tensor([r["y_scaled"] for r in examples], dtype=torch.float32)
    if x.shape[1:] != (24, 7) or c.shape[1:] != (24, 5) or y.shape[1:] != (24,):
        raise ValueError("Invalid training tensor shape")
    if not all(torch.isfinite(v).all() for v in (x, c, y)) or (y < 0).any():
        raise ValueError("Nonfinite/negative training values")
    if not ((x[:, :, -1] == 0) | (x[:, :, -1] == 1)).all() or (x[:, :, -1].sum(1) == 0).any():
        raise ValueError("Invalid history mask")
    original = torch.tensor([r["y_kwh"] for r in examples])
    scales = torch.tensor([r["forecast"]["energy_scale"] for r in examples])
    if not torch.allclose(y * scales[:, None], original, atol=1e-4, rtol=1e-5):
        raise ValueError("Scaled labels do not match original units")
    return x, c, y


def source_signature(examples: list[dict]) -> str:
    """Compare source content across budget containers, excluding only container ID."""
    digest = hashlib.sha256()
    for row in examples:
        if row["role"] != "source":
            raise ValueError("Source signature cannot contain target examples")
        forecast = {k: v for k, v in row["forecast"].items() if k != "input_run_id"}
        digest.update(json.dumps(dict(row, forecast=forecast), sort_keys=True).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def arrived(record: dict, as_of: datetime) -> tuple[float, ...] | None:
    return ready_labels(
        LabelRecord(
            identity=tuple(record["identity"]),
            origin=datetime.fromisoformat(record["origin"]),
            clock_mode=record["clock_mode"],
            timestamps=tuple(map(datetime.fromisoformat, record["timestamps"])),
            energy_kwh=tuple(record["energy_kwh"]),
            file_valid=tuple(record["file_valid"]),
            available_at=tuple(
                datetime.fromisoformat(v) if v else None for v in record["available_at"]
            ),
        ),
        as_of=as_of,
    )
