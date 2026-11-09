"""Preflight that issue #99 registered origin strings match replay serialization."""

import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from ev_models.data import InputRun
from ev_runner.replay import Replay
from ev_search.protocol import require_scored_bindings

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "configs" / "issue99-protocol-locked-v1.json"
V2 = ROOT / "configs" / "issue99-protocol-locked-v2.json"
INPUTS = ROOT / ".cache" / "issue99-input14"
ZONE = timezone(timedelta(hours=8))


class ProtocolOriginPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = json.loads(V2.read_text(encoding="utf-8"))

    def test_revision_preserves_all_non_origin_settings_and_instants(self) -> None:
        previous_bytes = V1.read_bytes()
        self.assertEqual(
            hashlib.sha256(V2.read_bytes()).hexdigest(),
            "f104d8809e04d0cde7d8982efd8146788f32c3c9a1c561ee9309891e6b040eb0",
        )
        previous = json.loads(previous_bytes)
        current = json.loads(V2.read_text(encoding="utf-8"))
        self.assertEqual(
            current.pop("supersedes_protocol_sha256"), hashlib.sha256(previous_bytes).hexdigest()
        )
        self.assertIn("string-based objective matching", current.pop("revision_note"))
        for phase in ("calibration", "evaluation"):
            for target, origins in previous[f"{phase}_origins"].items():
                normalized = [
                    datetime.fromisoformat(row).astimezone(ZONE).isoformat() for row in origins
                ]
                self.assertEqual(current[f"{phase}_origins"][target], normalized)
                previous[f"{phase}_origins"][target] = normalized
        self.assertEqual(current, previous)

    def test_registered_strings_are_replay_local_midnights(self) -> None:
        start = datetime(2022, 12, 1, tzinfo=ZONE)
        replay_strings = {(start + timedelta(days=day)).isoformat() for day in range(90)}
        for phase, expected_count in (("calibration", 19), ("evaluation", 28)):
            for target in self.protocol["targets"]:
                with self.subTest(phase=phase, target=target):
                    origins = self.protocol[f"{phase}_origins"][target]
                    self.assertEqual(len(origins), expected_count)
                    self.assertEqual(len(origins), len(set(origins)))
                    self.assertTrue(set(origins) <= replay_strings)
                    self.assertTrue(all(row.endswith("T00:00:00+08:00") for row in origins))

    @unittest.skipUnless(INPUTS.is_dir(), "Identified local 14-day input is unavailable")
    def test_registered_strings_match_actual_replay_forecasts(self) -> None:
        inputs = InputRun(INPUTS, self.protocol["input_manifest_sha256"])
        self.assertEqual(inputs.deployment.isoformat(), "2022-12-01T00:00:00+08:00")
        for target in self.protocol["targets"]:
            replay = Replay(inputs, target, 90)
            emitted = {origin.isoformat() for origin in replay.forecasts}
            for phase in ("calibration", "evaluation"):
                with self.subTest(phase=phase, target=target):
                    self.assertTrue(set(self.protocol[f"{phase}_origins"][target]) <= emitted)

    def test_immutable_scorer_commit_and_study_bindings(self) -> None:
        config_bytes = (ROOT / "configs" / "issue99-fixed-search-v1.json").read_bytes()
        for phase in ("calibration", "evaluation"):
            study = json.loads((ROOT / "configs" / f"issue99-study-{phase}-v1.json").read_text())
            with (
                self.subTest(phase=phase),
                patch(
                    "ev_search.protocol.code_identity",
                    return_value={"commit": self.protocol["code_commit"]},
                ),
            ):
                require_scored_bindings(
                    self.protocol,
                    study,
                    fixed_search_config_sha256=hashlib.sha256(config_bytes).hexdigest(),
                    phase=phase,
                )


if __name__ == "__main__":
    unittest.main()
