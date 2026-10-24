"""Checkpoint publication on filesystems without hard-link support."""

from __future__ import annotations

import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.hung_sprint2._create_only import publish_create_only


@unittest.skipIf(os.name == "nt", "Drive FUSE fallback applies on POSIX")
class CreateOnlyFallbackTests(unittest.TestCase):
    def test_drive_fallback_copies_and_never_replaces(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            temporary = root / "checkpoint.tmp"
            destination = root / "checkpoint.pt"
            temporary.write_bytes(b"first checkpoint")
            with patch(
                "experiments.hung_sprint2._create_only.os.link",
                side_effect=PermissionError(errno.EPERM, "Drive FUSE rejects hard links"),
            ):
                publish_create_only(temporary, destination)
                self.assertEqual(destination.read_bytes(), b"first checkpoint")
                temporary.write_bytes(b"second checkpoint")
                with self.assertRaises(FileExistsError):
                    publish_create_only(temporary, destination)
            self.assertEqual(destination.read_bytes(), b"first checkpoint")


if __name__ == "__main__":
    unittest.main()
