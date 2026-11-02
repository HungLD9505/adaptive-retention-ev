"""Publish a finished checkpoint without replacing an existing artifact."""

from __future__ import annotations

import errno
import os
import shutil
from pathlib import Path


def publish_create_only(temporary: Path, destination: Path) -> None:
    """Use an atomic hard link, with an exclusive-copy fallback for Drive FUSE.

    Google Drive's Colab mount rejects hard links. The fallback still refuses
    an existing destination; its incomplete copy remains inspectable if I/O
    fails, and the run manifest is written only after checkpoint verification.
    """
    if os.name == "nt":
        os.rename(temporary, destination)
        return
    try:
        os.link(temporary, destination)
        return
    except OSError as error:
        if error.errno not in {errno.EPERM, errno.EOPNOTSUPP, errno.EXDEV}:
            raise
    with temporary.open("rb") as source, destination.open("xb") as target:
        shutil.copyfileobj(source, target)
        target.flush()
        os.fsync(target.fileno())
