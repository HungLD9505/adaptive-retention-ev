"""Read-only guard checks for Colab #39 peer artifact verification."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.hung_colab39_peer_readback import FILE_MAP, FILE_MAP_SHA256, ROOT, read_map, verify


class Colab39PeerReadbackTests(unittest.TestCase):
    def test_pinned_map_has_exact_identity(self) -> None:
        rows = read_map(FILE_MAP, FILE_MAP_SHA256)
        self.assertEqual(len(rows), 163)
        self.assertEqual(sum(int(row["bytes"]) for row in rows), 72_529_254)

    def test_verify_detects_changed_missing_and_extra_bytes(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            folder = Path(directory)
            first = folder / "7d" / "run" / "checkpoint.pt"
            first.parent.mkdir(parents=True)
            first.write_bytes(b"first")
            second = folder / "matrix_identity.json"
            second.write_bytes(b"second")
            rows = [
                {
                    "path": path.relative_to(folder).as_posix(),
                    "bytes": str(path.stat().st_size),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in (first, second)
            ]
            self.assertEqual(verify(folder, rows)["status"], "VERIFIED")

            first.write_bytes(b"other")
            changed = verify(folder, rows)
            self.assertEqual(changed["status"], "FAILED")
            self.assertIn("SHA-256 mismatch: 7d/run/checkpoint.pt", changed["failures"])

            second.unlink()
            (folder / "extra.txt").write_text("extra", encoding="utf-8")
            incomplete = verify(folder, rows)
            self.assertEqual(incomplete["status"], "FAILED")
            self.assertEqual(incomplete["missing"], ["matrix_identity.json"])
            self.assertEqual(incomplete["unexpected"], ["extra.txt"])


if __name__ == "__main__":
    unittest.main()
