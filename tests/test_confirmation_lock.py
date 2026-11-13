"""Outcome-blind cohort selection and fail-closed execution recipe/commit guards."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.confirmation_lock import select_entities
from tools.confirmation_run import validate_lock, validate_recipe


def protocol():
    return {
        "schema": "new-entity-confirmation-lock-v1",
        "execution_authorized": True,
        "recipe": {
            "initial_weight": 0.4307815378871372,
            "eta": 0.1,
            "share": 0.1,
            "stable_lambda": 1.0,
            "fast_lambda": 0.0,
            "fast_window_days": 7,
            "initial_epochs": 3,
            "online_epochs": 1,
            "learning_rate": 0.001,
            "batch_size": 64,
        },
        "seeds": [42, 43, 44],
        "history_days": 14,
        "scheduled_days": 90,
        "groups": [{"selected_ids": ["001"], "sources": {"42": {}, "43": {}, "44": {}}}],
    }


class ConfirmationLockTests(unittest.TestCase):
    def test_selection_ignores_outcomes_and_input_order_and_excludes_prior_use(self):
        rows = [
            {
                "identity": ["charged", "AMS", i],
                "role": "development",
                "status": "ready",
                "initial_trainable": 13,
                "mae": value,
            }
            for i, value in [("001", 999), ("002", 1), ("003", 0)]
        ]
        selected = select_entities(rows, {"002"}, "charged-AMS", cap=2)
        modified = copy.deepcopy(list(reversed(rows)))
        for r in modified:
            r["mae"] = -10000
        self.assertEqual(selected, select_entities(modified, {"002"}, "charged-AMS", cap=2))
        self.assertEqual({r["entity_id"] for r in selected}, {"001", "003"})
        rows[0]["role"] = "source"
        rows[2]["initial_trainable"] = 0
        self.assertEqual(select_entities(rows, {"002"}, "charged-AMS"), [])

    def test_recipe_seed_and_duplicate_target_changes_fail_before_data_access(self):
        base = protocol()
        validate_recipe(base)
        for altered in [dict(base, history_days=7), dict(base, seeds=[42, 43])]:
            with self.assertRaises(ValueError):
                validate_recipe(altered)
        altered = copy.deepcopy(base)
        altered["recipe"]["eta"] = 1
        with self.assertRaises(ValueError):
            validate_recipe(altered)
        altered = copy.deepcopy(base)
        altered["groups"][0]["selected_ids"] = ["001", "001"]
        with self.assertRaises(ValueError):
            validate_recipe(altered)

    def test_uncommitted_lock_or_changed_executed_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "runner.py"
            source.write_text("unchanged")
            lock = protocol()
            lock["executed_code_sha256"] = {
                "runner.py": hashlib.sha256(source.read_bytes()).hexdigest()
            }
            path = root / "lock.json"
            data = json.dumps(lock).encode()
            path.write_bytes(data)
            with (
                patch("tools.confirmation_run.ROOT", root),
                patch("tools.confirmation_run.subprocess.check_output", return_value=data),
            ):
                self.assertEqual(validate_lock(path)["seeds"], [42, 43, 44])
                path.write_bytes(data + b" ")
                with self.assertRaisesRegex(ValueError, "committed unchanged"):
                    validate_lock(path)
                path.write_bytes(data)
                source.write_text("tampered")
                with self.assertRaisesRegex(ValueError, "code changed"):
                    validate_lock(path)


if __name__ == "__main__":
    unittest.main()
