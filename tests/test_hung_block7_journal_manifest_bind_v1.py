"""Guard against a correct journal SHA paired to the wrong resume state."""

import unittest

from tools.hung_block7_journal_manifest_bind_v1 import validate_binding


class JournalManifestBindingTests(unittest.TestCase):
    def test_rejects_wrong_resume_checkpoint(self):
        row = {"run_id": "block7_example", "sha256": "a" * 64}
        header = {
            "schema": "hung-sprint2-event-journal-v1",
            "start_event_index": 47,
            "input_binding": {"entity_id": "1025"},
            "resumed_from": {"run_id": "replay-21", "checkpoint_sha256": "b" * 64},
        }
        manifest = {
            "event_journal": {
                "file": "events.jsonl",
                "sha256": row["sha256"],
                "start_event_index": 47,
                "end_event_index": 49,
                "events_written": 2,
            },
            "input_binding": header["input_binding"],
            "resumed_from": {"run_id": "replay-21", "checkpoint_sha256": "c" * 64},
            "runner_cursor": 90,
        }
        with self.assertRaisesRegex(ValueError, "Resume binding mismatch"):
            validate_binding(row, manifest, header, 2)
