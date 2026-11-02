"""Backup recovery rejects archive corruption and path/report ambiguity."""

import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.recover_controller import inspect_chunk


class RecoveryTests(unittest.TestCase):
    def test_complete_report_and_extra_matrix_label_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chunk.zip"
            with zipfile.ZipFile(path, "x") as z:
                z.writestr("completed-runs.json", json.dumps([{"run_id": "fixture", "recipe": 1}]))
                z.writestr("study/fixture/run.json", json.dumps({"run_id": "fixture"}))
                z.writestr("study/fixture/tick-0000/state.pt", b"fixture")
            self.assertEqual(inspect_chunk(path), [{"run_id": "fixture", "recipe": 1}])

    def test_unsafe_extra_symlink_duplicate_or_contradictory_members_fail(self):
        cases = ("traversal", "extra", "symlink", "duplicate", "contradictory", "bad_run_id")
        for case in cases:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "chunk.zip"
                with zipfile.ZipFile(path, "x") as z:
                    row = {"run_id": "../outside" if case == "bad_run_id" else "fixture"}
                    z.writestr("completed-runs.json", json.dumps([row]))
                    z.writestr(
                        "study/fixture/run.json",
                        json.dumps({"run_id": "other" if case == "contradictory" else "fixture"}),
                    )
                    if case == "traversal":
                        z.writestr("study/fixture/../../outside", b"bad")
                    if case == "extra":
                        z.writestr("study/unlisted/file", b"bad")
                    if case == "duplicate":
                        import warnings

                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", UserWarning)
                            z.writestr("study/fixture/run.json", b"{}")
                    if case == "symlink":
                        info = zipfile.ZipInfo("study/fixture/link")
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        z.writestr(info, b"/outside")
                with self.assertRaises(ValueError):
                    inspect_chunk(path)


if __name__ == "__main__":
    unittest.main()
