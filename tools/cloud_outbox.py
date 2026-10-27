"""Explicit managed-runtime roots; this choice does not approve an environment profile."""

from pathlib import Path

CLOUD_ROOTS = ("/kaggle/working", "/content")


def cloud_working_root(value: str = CLOUD_ROOTS[0]) -> Path:
    """Select Kaggle or Colab without allowing an arbitrary output-root override."""
    if not isinstance(value, str) or value not in CLOUD_ROOTS:
        raise ValueError("Cloud root must be exactly /kaggle/working or /content")
    return Path(value)


def crosses_mounted_storage(output: Path, working: Path) -> bool:
    """Keep scratch outboxes off nested mounts, including Colab's reserved Drive path."""
    target, cloud = output.resolve(), working.resolve()
    if not target.is_relative_to(cloud):
        return False  # The caller separately rejects paths outside its cloud root.
    if cloud == Path("/content").resolve() and target.is_relative_to(cloud / "drive"):
        return True
    for ancestor in (target, *target.parents):
        if ancestor == cloud:
            return False
        if ancestor.is_mount():
            return True
    return False
