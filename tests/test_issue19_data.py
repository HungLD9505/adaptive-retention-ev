"""Independent producer fixtures through the accepted #18 loader and #19 consumer."""

import json
import unittest
from unittest.mock import patch

import test_input_loader as input_fixtures
import torch

from ev_inputs.loader import MISSING_DATA_POLICY
from ev_models.checkpoint import digest, load_checkpoint
from ev_models.data import InputRun
from ev_models.run import execute, validate_config


class InputModelTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.fixture = input_fixtures.LoaderTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.fixture.run_loader("inputs", missing_data_policy=MISSING_DATA_POLICY)
        self.inputs_root = self.root / "inputs"
        self.inputs = InputRun(self.inputs_root, digest(self.inputs_root / "manifest.json"))
        self.config = {
            "training": {
                "seed": 42,
                "epochs": 1,
                "batch_size": 64,
                "learning_rate": 0.001,
                "epsilon": 0.001,
                "head_width": 64,
            },
            "lambda": 0,
            "development_entities": ["005"],
            "evaluation_origins": 2,
        }

    def test_source_target_end_to_end_and_predictions_before_labels(self):
        src = execute("source", self.inputs, self.config, self.root / "source", device="cpu")
        self.assertEqual(src["training_examples"], 29)
        target_config = {**self.config, "lambda": 0.01}
        original = self.inputs.verify

        def verify(name):
            if name == "labels.jsonl":
                self.assertTrue((self.root / "target/predictions.jsonl").exists())
            return original(name)

        with patch.object(self.inputs, "verify", side_effect=verify):
            result = execute(
                "target",
                self.inputs,
                target_config,
                self.root / "target",
                device="cpu",
                source_path=self.root / "source/final.pt",
                source_sha256=src["checkpoint_sha256"],
                entity_id="005",
            )
        self.assertEqual(result["training_examples"], 6)
        self.assertEqual(result["metrics"]["scored_complete_days"], 2)
        self.assertGreaterEqual(result["metrics"]["mae_kwh"], 0)
        self.assertEqual(result["input_binding"]["entity_id"], "005")
        self.assertEqual(result["input_binding"]["history_days"], 7)
        self.assertEqual(digest(self.root / "source/final.pt"), src["checkpoint_sha256"])

    def test_final_target_and_bad_config_rejected(self):
        for role, entity in [("final", None), ("development", "001"), ("source", "005")]:
            with self.assertRaises(ValueError):
                self.inputs.training(role, entity)
        for update in (
            {"lambda": -1},
            {"evaluation_origins": 0},
            {"development_entities": ["005", "005"]},
            {"extra": 1},
        ):
            with self.assertRaises(ValueError):
                validate_config({**self.config, **update})

    def test_hash_corruption_rejected(self):
        with self.assertRaises(ValueError):
            InputRun(self.inputs_root, "0" * 64)
        with (self.inputs_root / "training.jsonl").open("a") as f:
            f.write("{}\n")
        with self.assertRaises(ValueError):
            InputRun(self.inputs_root, digest(self.inputs_root / "manifest.json"))

    def mutate_training(self, change):
        p = self.inputs_root / "training.jsonl"
        rows = [json.loads(x) for x in p.read_text().splitlines()]
        rows = [change(x) for x in rows]
        p.write_text("".join(json.dumps(x) + "\n" for x in rows))
        mpath = self.inputs_root / "manifest.json"
        m = json.loads(mpath.read_text())
        m["files"]["training.jsonl"] = {"sha256": digest(p), "size_bytes": p.stat().st_size}
        mpath.write_text(json.dumps(m))
        return InputRun(self.inputs_root, digest(mpath))

    def test_resigned_invalid_prefix_or_label_rejected(self):
        def mutate(r):
            if r["role"] == "source":
                r["y_scaled"][0] = None
            return r

        inp = self.mutate_training(mutate)
        with self.assertRaises((ValueError, TypeError)):
            inp.training("source")

    def test_future_prefix_boundary_rejected(self):
        row = self.inputs.training("source")[0]
        row["origin"] = self.inputs.deployment.isoformat()
        # Origin alone is already inconsistent; full shifts are rejected at prefix gate too.
        with self.assertRaises(ValueError):
            self.inputs.validate_forecast(row, role="source", before_deployment=True)

    def test_budget_source_compatibility_and_exact_prefix_counts(self):
        for days in (14, 28):
            self.fixture.run_loader(
                f"inputs-{days}", history_days=days, missing_data_policy=MISSING_DATA_POLICY
            )
            root = self.root / f"inputs-{days}"
            inp = InputRun(root, digest(root / "manifest.json"))
            self.assertEqual(inp.source_hash, self.inputs.source_hash)
            self.assertEqual(len(inp.training("development", "005")), days - 1)

    def test_replay_label_mutation_cannot_change_source_training(self):
        before = self.inputs.training("source")
        (self.inputs_root / "labels.jsonl").write_text("unread corrupted future data")
        after = InputRun(self.inputs_root, digest(self.inputs_root / "manifest.json")).training(
            "source"
        )
        self.assertEqual(before, after)

    def test_source_only_target_keeps_weights_and_records_initialization(self):
        src = execute("source", self.inputs, self.config, self.root / "source", device="cpu")
        before, _, _ = load_checkpoint(
            self.root / "source/final.pt", sha256=src["checkpoint_sha256"]
        )
        with patch.object(self.inputs, "training", return_value=[]):
            result = execute(
                "target",
                self.inputs,
                self.config,
                self.root / "target",
                device="cpu",
                source_path=self.root / "source/final.pt",
                source_sha256=src["checkpoint_sha256"],
                entity_id="005",
            )
        after, _, _ = load_checkpoint(
            self.root / "target/final.pt", sha256=result["checkpoint_sha256"]
        )
        self.assertEqual(result["initialization"], "source_checkpoint_only")
        for k, v in before.state_dict().items():
            self.assertTrue(torch.equal(v, after.state_dict()[k]))

    def test_source_nonempty_and_resume_config_guards(self):
        with patch.object(self.inputs, "training", return_value=[]):
            with self.assertRaises(ValueError):
                execute("source", self.inputs, self.config, self.root / "empty", device="cpu")
        src = execute("source", self.inputs, self.config, self.root / "source", device="cpu")
        with self.assertRaises(ValueError):
            execute(
                "source",
                self.inputs,
                {**self.config, "evaluation_origins": 1},
                self.root / "resume",
                device="cpu",
                resume=self.root / "source/final.pt",
                resume_sha256=src["checkpoint_sha256"],
            )
