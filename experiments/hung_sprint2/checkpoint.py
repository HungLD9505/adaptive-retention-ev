"""Create-only runner snapshots bound to the accepted target input identity."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import torch

from experiments.hung_sprint2.runner import PrequentialRunner


def save_runner(path: Path, runner: PrequentialRunner) -> None:
    """Save a complete snapshot atomically without replacing an old run."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    if not path.parent.is_dir():
        raise FileNotFoundError(path.parent)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            torch.save(runner.state_dict(), stream)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows rename fails if the destination exists; POSIX link is the
        # create-only atomic publication primitive. Neither replaces a run.
        if os.name == "nt":
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_runner(path: Path, *, expected_binding: dict) -> PrequentialRunner:
    """Verify the accepted input binding before restoring an event cursor."""
    state = torch.load(Path(path), map_location="cpu", weights_only=True)
    return PrequentialRunner.from_state_dict(state, expected_binding=expected_binding)
