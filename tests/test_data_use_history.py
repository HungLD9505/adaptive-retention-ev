"""Distinguish declared model uses from catalogue metadata without reading scores."""

import json
import unittest

from tools.data_use_history import extract, target_ids


class DataUseHistoryTests(unittest.TestCase):
    def test_jsonl_keeps_every_execution_record_and_run_id(self):
        data = b'{"target":"001","namespace":"charged-AMS"}\n{"run_id":"cyber_v3_gru_transfer_1405_42"}\n'
        self.assertEqual(
            extract(data, "member_studies/cyber/execution_log.jsonl"),
            {("charged-AMS", "001"), ("urbanev-SZH", "1405")},
        )

    def test_jsonl_identity_without_role_is_conservative_but_source_is_skipped(self):
        data = b'{"identity":["charged","JHB","21"]}\n{"identity":["charged","JHB","22"],"role":"source"}\n'
        self.assertEqual(extract(data, "execution.jsonl"), {("charged-JHB", "21")})

    def test_malformed_jsonl_cannot_silently_lose_later_records(self):
        for data in (b'{"target":"1"}\n{"target":', b"[]\n", b"\xff"):
            with self.assertRaises((ValueError, UnicodeDecodeError)):
                extract(data, "run.jsonl")

    def test_nested_run_binding_is_namespace_specific(self):
        value = {
            "binding": {
                "input": {
                    "dataset_id": "charged",
                    "city_id": "JHB",
                    "entity_id": "21",
                    "stage": "target",
                }
            }
        }
        self.assertEqual(target_ids(value, "run.json"), {("charged-JHB", "21")})

    def test_source_records_are_not_target_exposure(self):
        self.assertEqual(
            target_ids(
                {"role": "source", "entity_id": "21", "namespace": ["charged", "JHB"]}, "run.json"
            ),
            set(),
        )

    def test_catalogue_and_preflight_are_not_executed_models(self):
        data = b"station_id,longitude,latitude\n1022,1,2\n"
        self.assertEqual(extract(data, "reports/data/entity_metadata.csv"), set())
        data = b"entity_id,initial_trainable_14d,scheduled_forecasts\n1022,13,90\n"
        self.assertEqual(extract(data, "scope_gap.csv"), set())
        value = {
            "decision": "INPUT_DISPOSITION_ONLY_REVIEWED_EXTENSION_PROTOCOL_REQUIRED",
            "entity_id": "1022",
        }
        self.assertEqual(extract(json.dumps(value).encode(), "omitted-disposition.json"), set())

    def test_scored_csv_and_explicit_city_keep_leading_zero_identity(self):
        data = b"namespace,target,mae_kwh\ncharged-AMS,001,999\n"
        self.assertEqual(extract(data, "ledger.csv"), {("charged-AMS", "001")})
        self.assertEqual(
            target_ids({"city": "Melbourne", "selected_ids": ["47"]}, "cohort.json"),
            {("charged-MEL", "47")},
        )

    def test_ambiguous_target_stays_ambiguous_not_assigned_to_convenient_city(self):
        self.assertEqual(target_ids({"target": "44"}, "legacy-run.json"), {("*", "44")})
        self.assertEqual(
            target_ids({"excluded_ids_from_tracked_metadata": ["1022"]}, "inventory.json"), set()
        )


if __name__ == "__main__":
    unittest.main()
