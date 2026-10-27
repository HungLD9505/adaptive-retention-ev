"""Independent simulated provider stages; no network, credentials or training."""

import ast
import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools import hung_kaggle_metric_queue as inventory
from tools import hung_kaggle_output_queue as output
from tools import hung_kaggle_queue as queue


class OutputQueueTests(unittest.TestCase):
    def test_packaged_programs_match_immutable_manifest(self):
        notebook = json.loads(
            Path("experiments/hung_sprint2/kaggle_output_dispatch_cpu_v1.ipynb").read_text(
                encoding="utf-8"
            )
        )
        manifest = json.loads(
            Path("experiments/hung_sprint2/kaggle_output_dispatch_manifest_v1.json").read_text(
                encoding="utf-8"
            )
        )
        outer = ast.parse("".join(notebook["cells"][0]["source"]))
        program = next(
            ast.literal_eval(node.value)
            for node in outer.body
            if isinstance(node, ast.Assign) and node.targets[0].id == "SOURCE"
        )
        self.assertEqual(
            hashlib.sha256(program.encode()).hexdigest(), manifest["launcher_source_sha256"]
        )
        literals = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in ast.parse(program).body
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        }
        scope = {}
        exec(literals["BUNDLE"], scope)  # Definitions only: never execute the launcher.
        self.assertEqual(sum(group["jobs"] for group in manifest["groups"]), 380)
        for group in manifest["groups"]:
            index = group["index"]
            source = scope["output_gpu_source"](
                literals["QUEUE_MODULE"],
                literals["SETUP"],
                literals["PARITY"],
                index,
                build=scope["gpu_source"],
            )
            self.assertEqual(
                hashlib.sha256(source.encode()).hexdigest(), group["gpu_source_sha256"]
            )
            proof = scope["output_readback_source"](literals["QUEUE_MODULE"], index)
            self.assertEqual(hashlib.sha256(proof.encode()).hexdigest(), group["cpu_source_sha256"])
            for shard, pins in group["shards"].items():
                self.assertEqual(pins["jobset_sha256"], scope["EXPECTED_JOBSET_SHA"][shard])
                self.assertEqual(
                    (pins["runtime_plan_sha256"], pins["runtime_partition_sha256"]),
                    scope["EXPECTED_PROVIDER_PINS"][shard],
                )

    def fake_gpu(self, module, setup, parity, index):
        return (
            f"\nclaim({output.gpu_name(index)!r}+'-execute', {{}})\n"
            + "for record in []:\n"
            + output.PENDING_STORAGE
            + "\n"
        )

    def simulate(
        self,
        root,
        *,
        status=None,
        exists=None,
        quota=None,
        index=2,
        phase="predecessor",
        ordinal=0,
        clock=(0, 10801),
    ):
        submit = Mock(side_effect=lambda name, source, **kw: {"name": name, "version": 1})
        with (
            patch.object(output, "Path", return_value=root / "relay"),
            patch.object(output.time, "monotonic", side_effect=clock),
            patch.object(output.time, "sleep"),
        ):
            output.run_output_queue(
                "pass",
                "pass",
                "pass",
                "pass",
                index,
                ordinal,
                phase,
                submit=submit,
                status=status or Mock(return_value="COMPLETE"),
                exists=exists or Mock(return_value=True),
                quota=quota or Mock(return_value=100000),
                claim_fn=Mock(),
                build_gpu=self.fake_gpu,
            )
        return submit

    def test_fixed_remaining_route_and_names_preserve_readers(self):
        flat = [s for i in range(2, 7) for s in output.OUTPUT_GROUPS[i]]
        self.assertEqual(set(flat), {*range(14, 29), 33, 34, 35, 36})
        self.assertEqual(len(flat), len(set(flat)))
        self.assertEqual(len(flat) * 20, 380)
        self.assertFalse(set(flat) & queue.LOCAL)
        for index in range(2, 7):
            self.assertEqual(output.gpu_name(index), queue.slug(index))
            for name in (
                output.gpu_name(index) + "-execute",
                output.readback_name(index) + "-submit",
            ):
                self.assertLessEqual(len(name), 50)

    def test_exact_full_execution_programs_and_bundle_compile(self):
        qtext = queue.compose_module_source(
            Path(queue.__file__).read_text(encoding="utf-8"), "pass"
        )
        n = json.loads(Path("experiments/hung_sprint2/kaggle_matched_group02.ipynb").read_text())
        setup, parity = ("".join(n["cells"][i]["source"]) for i in (1, 3))
        bundle = output.bundle_sources(
            qtext,
            Path(output.__file__).read_text(encoding="utf-8"),
            inspect.getsource(inventory.owned_kernel_exists),
        )
        scope = {}
        exec(bundle, scope)
        for index in range(2, 7):
            source = output.output_gpu_source(qtext, setup, parity, index, build=queue.gpu_source)
            body = source[source.index(f"\nclaim({output.gpu_name(index)!r}+'-execute'") :]
            self.assertNotIn(output.PENDING_STORAGE, body)
            self.assertIn("assert passed", body)
            self.assertIn("8*1024**3", body)
            self.assertIn(f"selected = {[f'shard_{n:04d}' for n in queue.GROUPS[index]]!r}", body)
            for phase in ("predecessor", "gpu", "readback"):
                compile(
                    output.launcher_source(bundle, qtext, setup, parity, index, 0, phase),
                    "controller",
                    "exec",
                )
            proof = output.output_readback_source(qtext, index)
            self.assertIn(f"{output.OUTPUT_GROUPS[index]!r}", proof)
            self.assertIn("assert not __import__('torch').cuda.is_available()", proof)
        self.assertIs(scope["run_output_queue"].__globals__["gpu_source"], scope["gpu_source"])
        with self.assertRaises(AssertionError):
            output.output_gpu_source(qtext, setup, parity, 1, build=queue.gpu_source)
        with self.assertRaises(AssertionError):
            output.output_gpu_source("pass", "pass", "pass", 2, build=lambda *a: "changed template")

    def test_all_five_groups_require_alternating_cpu_readback(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            root = Path(tmp)
            calls = self.simulate(root, clock=(0, 0, 0, 0, 0)).call_args_list
            self.assertEqual(len(calls), 10)
            for offset, index in enumerate(range(2, 7)):
                gpu, cpu = calls[2 * offset : 2 * offset + 2]
                self.assertTrue(gpu.kwargs["gpu"])
                self.assertEqual(gpu.args[0], output.gpu_name(index))
                self.assertEqual(gpu.kwargs["predecessor"], output.gpu_name(index - 1))
                self.assertFalse(cpu.kwargs["gpu"])
                self.assertEqual(cpu.kwargs["datasets"], [])
                self.assertEqual(cpu.kwargs["predecessor"], output.gpu_name(index))
                receipt = json.loads(
                    (root / "relay" / f"group-{index:02d}-verified.json").read_text()
                )
                self.assertEqual(receipt["shards"], list(output.OUTPUT_GROUPS[index]))
            self.assertTrue((root / "relay/complete.json").is_file())

    def test_unobserved_parent_proof_never_gets_status_or_gpu(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            state = Mock(return_value="COMPLETE")
            calls = self.simulate(
                Path(tmp), status=state, exists=Mock(return_value=False)
            ).call_args_list
            state.assert_called_once_with(output.gpu_name(1))
            self.assertEqual(len(calls), 1)
            self.assertFalse(calls[0].kwargs["gpu"])
            self.assertIn("relay-01", calls[0].args[0])

    def test_failed_prior_gpu_or_cpu_stops_before_next_execution(self):
        for states in (["ERROR"], ["COMPLETE", "ERROR"]):
            with self.subTest(states=states), tempfile.TemporaryDirectory(dir=".") as tmp:
                quota = Mock(return_value=100000)
                with self.assertRaises(AssertionError):
                    self.simulate(Path(tmp), status=Mock(side_effect=states), quota=quota)
                quota.assert_not_called()

    def test_quota_nan_or_insufficient_fails_before_gpu(self):
        for available in (float("nan"), 0, 17177):
            with self.subTest(available=available), tempfile.TemporaryDirectory(dir=".") as tmp:
                with self.assertRaises(AssertionError):
                    self.simulate(Path(tmp), quota=Mock(return_value=available))
                self.assertFalse(list((Path(tmp) / "relay").glob("*submission.json")))

    def test_running_gpu_handoff_never_resubmits_gpu(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            root = Path(tmp)
            calls = self.simulate(
                root, phase="gpu", status=Mock(return_value="RUNNING")
            ).call_args_list
            self.assertEqual(len(calls), 1)
            self.assertFalse(calls[0].kwargs["gpu"])
            state = json.loads((root / "relay/handoff.json").read_text())
            self.assertEqual(state["phase"], "gpu")
            self.assertEqual(state["index"], 2)

    def test_new_gpu_acknowledgement_is_carried_into_handoff(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            root = Path(tmp)
            calls = self.simulate(
                root, status=Mock(side_effect=["COMPLETE", "COMPLETE", "RUNNING"])
            ).call_args_list
            self.assertEqual(len(calls), 2)
            self.assertTrue(calls[0].kwargs["gpu"])
            self.assertFalse(calls[1].kwargs["gpu"])
            state = json.loads((root / "relay/handoff.json").read_text())
            self.assertEqual(state["phase"], "gpu")
            acknowledgement = json.loads((root / "relay/gpu-02-submission.json").read_text())
            self.assertEqual(acknowledgement["name"], output.gpu_name(2))

    def test_new_readback_acknowledgement_is_carried_into_handoff(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            root = Path(tmp)
            calls = self.simulate(
                root, phase="gpu", status=Mock(side_effect=["COMPLETE", "RUNNING"])
            ).call_args_list
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(call.kwargs["gpu"] is False for call in calls))
            self.assertEqual(calls[0].args[0], output.readback_name(2))
            self.assertEqual(
                json.loads((root / "relay/handoff.json").read_text())["phase"], "readback"
            )

    def test_running_readback_handoff_never_resubmits_readback(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            calls = self.simulate(
                Path(tmp), phase="readback", status=Mock(return_value="RUNNING")
            ).call_args_list
            self.assertEqual(len(calls), 1)
            self.assertIn("relay-01", calls[0].args[0])

    def test_last_readback_receipt_does_not_require_reexecution(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            calls = self.simulate(Path(tmp), index=6, phase="readback", clock=(0,)).call_args_list
            self.assertEqual(calls, [])
            self.assertTrue((Path(tmp) / "relay/group-06-verified.json").is_file())

    def test_error_in_current_gpu_or_readback_stops_without_receipt(self):
        for phase in ("gpu", "readback"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory(dir=".") as tmp:
                with self.assertRaises(AssertionError):
                    self.simulate(Path(tmp), phase=phase, status=Mock(return_value="ERROR"))
                self.assertFalse(list((Path(tmp) / "relay").glob("*verified.json")))

    def test_cpu_handoff_limit_stops_without_submission(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            with self.assertRaises(AssertionError):
                self.simulate(
                    Path(tmp), ordinal=11, phase="gpu", status=Mock(return_value="RUNNING")
                )

    def test_atomic_receipt_preserves_old_and_interrupted_outputs(self):
        with tempfile.TemporaryDirectory(dir=".") as tmp:
            path = Path(tmp) / "receipt.json"
            output.atomic_record(path, {"value": "original"})
            with self.assertRaises(FileExistsError):
                output.atomic_record(path, {"value": "unexpected"})
            self.assertEqual(json.loads(path.read_text()), {"value": "original"})
            interrupted = Path(tmp) / "interrupted.json"
            with patch.object(output.os, "link", side_effect=OSError("synthetic interruption")):
                with self.assertRaises(OSError):
                    output.atomic_record(interrupted, {"passed": True})
            self.assertFalse(interrupted.exists())
            self.assertTrue(interrupted.with_name("interrupted.json.partial").exists())
