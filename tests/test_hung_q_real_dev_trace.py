"""Small failure gates for the bounded real Development trace input reader."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.hung_q_real_dev_trace import BASE, load_input, selected_rows


class RealTraceInputTests(unittest.TestCase):
    def test_member_bytes_are_pinned_before_selected_rows_are_used(self) -> None:
        root = Path(__file__).resolve().parents[1] / ".cache"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            archive_path = Path(directory) / "fixture.zip"
            payload = (
                b'{"identity": ["urbanev", "SZH", "1001"], "origin": "day-1"}\n'
                b'{"identity": ["urbanev", "SZH", "other"], "origin": "day-1"}\n'
            )
            with ZipFile(archive_path, "w") as archive:
                archive.writestr(BASE + "forecasts.jsonl", payload)
            expected = {"sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}
            with ZipFile(archive_path) as archive:
                self.assertEqual(
                    selected_rows(archive, "forecasts.jsonl", expected),
                    [payload.splitlines(keepends=True)[0]],
                )
                with self.assertRaisesRegex(ValueError, "SHA/size mismatch"):
                    selected_rows(archive, "forecasts.jsonl", {**expected, "sha256": "0" * 64})

    def test_unpinned_input_zip_fails_before_decoding(self) -> None:
        root = Path(__file__).resolve().parents[1] / ".cache"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            archive_path = Path(directory) / "untrusted.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr(BASE + "manifest.json", "{}")
            with self.assertRaisesRegex(ValueError, "pinned DATA-v1"):
                load_input(archive_path)


if __name__ == "__main__":
    unittest.main()
