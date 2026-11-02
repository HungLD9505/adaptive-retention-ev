"""A corrupt saved journal must not enter the scientific comparison."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.hung_block7_journal_audit_v1 import load_segment


class JournalAuditTests(unittest.TestCase):
    def test_rejects_gap_in_resumed_event_indices(self):
        rows = [
            {"kind": "header", "run_id": "replay-90", "start_event_index": 47},
            {"kind": "event", "event_index": 47, "value": "forecast:2023-01-01T00:00:00+08:00"},
            {"kind": "event", "event_index": 49, "value": "score:2023-01-01T00:00:00+08:00"},
        ]
        with patch.object(Path, "read_text", return_value="\n".join(map(json.dumps, rows))):
            with self.assertRaisesRegex(ValueError, "Non-contiguous"):
                load_segment(Path("events.jsonl"))
