"""Small independent archive fixtures; no publisher scripts are executed."""

import io
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.charged_semantics import audit_ams, main


class SemanticsTests(unittest.TestCase):
    def fixture(self, duration: str | None = None) -> ZipFile:
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("AMS/volume.csv", ",0,1\nt0,0,1\nt1,0,0\n")
            archive.writestr("AMS/duration.csv", duration or ",0,1\nt0,0,0\nt1,0,2\n")
            archive.writestr(
                "AMS/sites.csv",
                "site_id,charger_num,total_volume,total_duration\n0,1,0,0\n1,1,3,4\n",
            )
            archive.writestr(
                "AMS/chargers.csv",
                "charger_id,site_id,total_volume,total_duration\na,0,0,0\nb,1,3,4\n",
            )
        stream.seek(0)
        archive = ZipFile(stream)
        self.addCleanup(archive.close)
        return archive

    def test_paired_zeros_static_and_hourly_are_distinguished(self) -> None:
        result = audit_ams(self.fixture())
        self.assertEqual(result["all_zero_volume_sites"], 1)
        self.assertEqual(result["both_all_zero_sites"], 1)
        self.assertEqual(result["all_zero_volume_but_positive_member_metadata"], 0)
        self.assertEqual(result["hourly_vs_static_volume_mismatches"], 1)
        self.assertEqual(result["static_site_vs_member_volume_mismatches"], 0)
        self.assertEqual(result["paired_cells"]["volume_positive_duration_zero"], 1)
        self.assertEqual(result["paired_cells"]["volume_zero_duration_positive"], 1)
        self.assertEqual(result["all_zero_volume_member_chargers"], 1)

    def test_truncation_clock_and_nonfinite_fail(self) -> None:
        for value in (",0,1\nt0,0,0\n", ",0,1\nt0,0,0\nwrong,0,2\n", ",0,1\nt0,NaN,0\nt1,0,2\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit_ams(self.fixture(value))

    def test_existing_evidence_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "evidence.json"
            output.write_text("preserve")
            self.assertEqual(main(["--output", str(output)]), 1)
            self.assertEqual(output.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
