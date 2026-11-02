"""Offline guards for frozen-input Block7 origin eligibility."""

from __future__ import annotations

import hashlib
import io
import json
import unittest
from datetime import datetime, timedelta, timezone
from zipfile import ZipFile

from tools.hung_block7_input_eligibility_audit import label_is_available, read_selected_member


class EligibilityTests(unittest.TestCase):
    def label(self) -> dict:
        origin = datetime(2022, 12, 1, tzinfo=timezone.utc)
        return {
            "origin": origin.isoformat(),
            "file_valid": [True] * 24,
            "energy_kwh": [1.0] * 24,
            "available_at": [
                (origin + timedelta(hours=hour + 1)).isoformat() for hour in range(24)
            ],
        }

    def test_complete_label_at_next_tick_is_eligible(self) -> None:
        self.assertTrue(label_is_available(self.label()))

    def test_missing_or_late_label_is_ineligible(self) -> None:
        missing = self.label()
        missing["file_valid"][2] = False
        self.assertFalse(label_is_available(missing))
        late = self.label()
        late["available_at"][23] = (
            datetime.fromisoformat(late["origin"]) + timedelta(days=1, seconds=1)
        ).isoformat()
        self.assertFalse(label_is_available(late))

    def test_rejects_nonfinite_or_short_complete_label(self) -> None:
        bad = self.label()
        bad["energy_kwh"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            label_is_available(bad)
        short = self.label()
        short["file_valid"].pop()
        with self.assertRaisesRegex(ValueError, "24 hours"):
            label_is_available(short)

    def test_member_hash_and_selection(self) -> None:
        data = b"".join(
            json.dumps({"identity": ["urbanev", "SZH", entity], "origin": "one"}).encode() + b"\n"
            for entity in ("1001", "1002")
        )
        memory = io.BytesIO()
        with ZipFile(memory, "w") as archive:
            archive.writestr("schedule.jsonl", data)
        memory.seek(0)
        with ZipFile(memory) as archive:
            spec = {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            selected = read_selected_member(archive, "schedule.jsonl", spec, {"1001"})
            self.assertEqual(len(selected["1001"]), 1)
            with self.assertRaisesRegex(ValueError, "Changed input member"):
                read_selected_member(
                    archive, "schedule.jsonl", {**spec, "sha256": "0" * 64}, {"1001"}
                )
