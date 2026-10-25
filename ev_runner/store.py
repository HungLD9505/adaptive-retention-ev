"""Immutable daily transactions; fail closed on interrupted, uncommitted ticks."""

import hashlib
import json
import os
import shutil
from pathlib import Path

import torch

from ev_models.checkpoint import digest
from ev_runner.state import canonical, torch_bytes


def sync_directory(path: Path) -> None:
    """Persist directory entries on POSIX before releasing an older checkpoint."""
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class Store:
    def __init__(self, root: Path, binding: dict, *, resume_from: Path | None = None) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=False)
        (root / "binding.json").write_bytes(canonical(binding))
        self.binding = binding
        config = binding.get("config")
        self.retention = config.get("state_retention", "all") if isinstance(config, dict) else "all"
        if self.retention not in {"all", "latest"}:
            raise ValueError("Unknown state-retention policy")
        self.count = 0
        self.previous = "0" * 64
        self.restored = None
        if resume_from:
            previous_binding = json.loads((resume_from / "binding.json").read_bytes())
            if previous_binding != binding:
                raise ValueError("Resume config/input/source/code/environment binding differs")
            if list(resume_from.glob(".pending-*")):
                raise ValueError(
                    "Uncommitted issued forecasts: preserve and inspect; no automatic rewrite"
                )
            ticks = sorted(resume_from.glob("tick-*"))
            for position, tick in enumerate(ticks):
                meta = json.loads((tick / "commit.json").read_bytes())
                if meta["previous"] != self.previous or meta["index"] != self.count:
                    raise ValueError("Broken chronological commit chain")
                for name, expected in meta["files"].items():
                    if (
                        name == "state.pt"
                        and not (tick / name).exists()
                        and self.retention == "latest"
                        and position < len(ticks) - 1
                    ):
                        continue
                    if (
                        name not in {"state.pt", "events.jsonl", "forecasts.json"}
                        or digest(tick / name) != expected
                    ):
                        raise ValueError("Changed committed run artifact")
                if set(meta["files"]) != {"state.pt", "events.jsonl", "forecasts.json"}:
                    raise ValueError("Incomplete tick manifest")
                shutil.copytree(tick, root / tick.name)
                self.previous = digest(tick / "commit.json")
                self.count += 1
            if not self.count:
                raise ValueError("No committed checkpoint to resume")
            self.restored = torch.load(
                root / f"tick-{self.count - 1:04d}/state.pt", weights_only=True
            )

    def begin(self) -> Path:
        path = self.root / f".pending-{self.count:04d}"
        path.mkdir(exist_ok=False)
        return path

    @staticmethod
    def save_forecasts(path: Path, predictions: dict) -> str:
        # This write is durable before caller can request labels for the issued day.
        with (path / "forecasts.json").open("xb") as stream:
            stream.write(canonical(predictions))
            stream.flush()
            os.fsync(stream.fileno())
        return digest(path / "forecasts.json")

    def commit(self, path: Path, state: dict, events: list[dict]) -> str:
        for name, data in (
            ("state.pt", torch_bytes(state)),
            ("events.jsonl", b"".join(canonical(e) for e in events)),
        ):
            with (path / name).open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        meta = {
            "index": self.count,
            "previous": self.previous,
            "files": {
                name: digest(path / name) for name in ("state.pt", "events.jsonl", "forecasts.json")
            },
        }
        with (path / "commit.json").open("xb") as stream:
            stream.write(canonical(meta))
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(path)
        os.replace(path, self.root / f"tick-{self.count:04d}")
        sync_directory(self.root)
        self.previous = hashlib.sha256(canonical(meta)).hexdigest()
        self.count += 1
        if self.retention == "latest":
            # The newest full model/optimizer/RNG/audit state is already committed.
            # Forecasts, events and historical state-hash commitments remain immutable.
            for old in self.root.glob("tick-*/state.pt"):
                if old.parent.name != f"tick-{self.count - 1:04d}":
                    old.unlink()
        return self.previous
