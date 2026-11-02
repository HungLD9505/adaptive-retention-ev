"""Recovery must exclude the completed shard and retain the original plan base."""

import ast
import json
import unittest
from pathlib import Path

from tools.hung_kaggle_queue import compose_module_source
from tools.hung_kaggle_recovery import (
    RECOVERY_SLUG,
    launcher_source,
    recovered_gpu_source,
    recovery_module,
    replace_once,
)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.module = compose_module_source(
            (root / "tools/hung_kaggle_queue.py").read_text(encoding="utf-8"),
            (root / "tools/hung_kaggle_storage.py").read_text(encoding="utf-8"),
        )
        notebook = json.loads(
            (
                root / "experiments/hung_sprint2/kaggle_development_cpu_coordinator_v2.ipynb"
            ).read_text(encoding="utf-8")
        )
        outer = ast.parse("".join(notebook["cells"][1]["source"]))
        inner = ast.literal_eval(outer.body[0].value.args[0])
        values = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in ast.parse(inner).body
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.targets[0], ast.Name)
        }
        self.setup, self.parity = values["SETUP"], values["PARITY"]

    def test_completed_shard_is_carried_but_not_executed(self):
        source = recovered_gpu_source(recovery_module(self.module), self.setup, self.parity)
        tree = ast.parse(source)
        selected = [
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "selected" for t in node.targets)
        ][-1]
        self.assertEqual(selected, [f"shard_{n:04d}" for n in range(9, 14)])
        self.assertIn("/kaggle/working/hung-matched-group03-v1", source)
        self.assertIn("carried / 'receipt.json'", source)
        self.assertIn("carried / 'artifacts.zip'", source)
        self.assertIn("assert readback[0]['sha256']", source)
        claims = [
            node.value
            for node in tree.body
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "claim"
        ]
        self.assertEqual(len(claims), 1)
        self.assertEqual(
            eval(compile(ast.Expression(claims[0].args[0]), "claim", "eval")),
            RECOVERY_SLUG + "-execute",
        )

    def test_recovery_redirect_is_limited_to_failed_group(self):
        scope = {}
        exec(recovery_module(self.module), scope)
        self.assertEqual(scope["slug"](1), RECOVERY_SLUG)
        self.assertEqual(scope["slug"](2), "hung-matched-group04-44b8532-20261027-v2")
        self.assertEqual(scope["GROUPS"][1], tuple(range(8, 14)))

    def test_source_drift_stops_preparation(self):
        for source in ("none", "marker marker"):
            with self.assertRaises(AssertionError):
                replace_once(source, "marker", "replacement")

    def test_launcher_requires_terminal_failure_and_independent_success(self):
        source = launcher_source(self.module, self.setup, self.parity)
        tree = ast.parse(source)
        barrier = [
            node
            for node in tree.body
            if isinstance(node, ast.Assert)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Call)
            and isinstance(node.test.left.func, ast.Name)
            and node.test.left.func.id == "status"
        ]
        self.assertEqual(len(barrier), 5)
        compiled = compile(ast.Module(body=barrier, type_ignores=[]), "barrier", "exec")
        for failed in ("RUNNING", "COMPLETE", "ERROR"):
            for readback in ("ERROR", "RUNNING", "COMPLETE"):
                statuses = [failed, failed, failed, failed, readback]
                if failed == "ERROR" and readback == "COMPLETE":
                    exec(compiled, {"status": lambda _: statuses.pop(0)})
                else:
                    with self.assertRaises(AssertionError):
                        exec(compiled, {"status": lambda _: statuses.pop(0)})


if __name__ == "__main__":
    unittest.main()
