"""Other roles/entities must be filtered before JSON value deserialization."""

import json
import unittest
from unittest.mock import patch

import test_issue19_data as fixtures


class ReaderTests(unittest.TestCase):
    setUp = fixtures.InputModelTests.setUp

    def assert_only_header_is_decoded(self, header, callback):
        original = json.loads
        decoded = []

        def guarded(value, *args, **kwargs):
            raw = value.encode() if isinstance(value, str) else value
            self.assertTrue(raw.startswith(header), "Unselected value arrays reached JSON decoder")
            decoded.append(raw)
            return original(value, *args, **kwargs)

        with patch("ev_models.data.json.loads", side_effect=guarded):
            result = callback()
        self.assertEqual(len(decoded), len(result))
        return result

    def test_source_does_not_decode_development_or_final_arrays(self):
        result = self.assert_only_header_is_decoded(
            b'{"role": "source", "forecast": {"identity": ',
            lambda: self.inputs.training("source"),
        )
        self.assertEqual(len(result), 29)

    def test_target_training_does_not_decode_other_entities(self):
        header = (
            '{"role": "development", "forecast": {"identity": '
            + json.dumps([*self.inputs.namespace, "005"])
            + ","
        ).encode()
        result = self.assert_only_header_is_decoded(
            header, lambda: self.inputs.training("development", "005")
        )
        self.assertEqual(len(result), 6)

    def test_replay_does_not_decode_other_entity_histories(self):
        header = (
            '{"role": "development", "identity": '
            + json.dumps([*self.inputs.namespace, "005"])
            + ","
        ).encode()
        result = self.assert_only_header_is_decoded(
            header, lambda: list(self.inputs.replay_forecasts("005"))
        )
        self.assertGreater(len(result), 0)

    def test_static_evaluation_decodes_only_issued_target_label_days(self):
        origin = self.inputs.deployment.isoformat()
        header = (
            '{"identity": '
            + json.dumps([*self.inputs.namespace, "005"])
            + ', "origin": "'
            + origin
            + '"'
        ).encode()
        result = self.assert_only_header_is_decoded(
            header, lambda: list(self.inputs.evaluation_labels("005", {origin}))
        )
        self.assertEqual(len(result), 1)

    def test_training_count_mismatch_fails_closed(self):
        self.inputs.entities[(*self.inputs.namespace, "005")]["initial_trainable"] += 1
        with self.assertRaises(ValueError):
            self.inputs.training("development", "005")

    def test_final_replay_and_training_are_rejected(self):
        identity = next(key for key, row in self.inputs.entities.items() if row["role"] == "final")
        with self.assertRaises(ValueError):
            list(self.inputs.replay_forecasts(identity[-1]))
        with self.assertRaises(ValueError):
            self.inputs.training("final", identity[-1])
        with self.assertRaises(ValueError):
            list(self.inputs.evaluation_labels(identity[-1], {self.inputs.deployment.isoformat()}))

    def test_selected_training_values_match_legacy_filter_exactly(self):
        expected = []
        for row in fixtures.InputRun(
            self.inputs_root, fixtures.digest(self.inputs_root / "manifest.json")
        ).training("development", "005"):
            expected.append(row)
        legacy = []
        for line in (self.inputs_root / "training.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["role"] == "development" and r["forecast"]["identity"][-1] == "005":
                forecast = self.inputs.validate_forecast(
                    {**r["forecast"], "role": "development"},
                    role="development",
                    before_deployment=True,
                )
                legacy.append({**forecast, "y_kwh": r["y_kwh"], "y_scaled": r["y_scaled"]})
        self.assertEqual(expected, legacy)


if __name__ == "__main__":
    unittest.main()
