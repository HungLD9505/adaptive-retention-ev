"""No-network regression for exactly-one missing shard and private output readback."""

import json
import unittest
from pathlib import Path

from tools import hung_kaggle_queue as queue
from tools import hung_kaggle_recovery13 as recovery


class Recovery13Tests(unittest.TestCase):
    def test_only_missing_shard_preserves_original_identity(self):
        notebook = json.loads(
            Path("experiments/hung_sprint2/kaggle_matched_group02.ipynb").read_text()
        )
        setup, parity = ("".join(notebook["cells"][i]["source"]) for i in (1, 3))
        module = queue.compose_module_source(Path(queue.__file__).read_text(), "pass")
        source = recovery.recovery_gpu(module, setup, parity)
        compile(source, "gpu", "exec")
        tail = source[source.index("claim('hung-group03-shard13-recovery") :]
        self.assertIn("selected = ['shard_0013']", tail)
        self.assertIn("hung-matched-group03-v1", tail)
        self.assertNotIn("    persist_shard(record,", tail)
        self.assertIn("assert passed", tail)
        self.assertIn("8*1024**3", tail)
        self.assertEqual(set(recovery.ARCHIVE_PINS), set(range(8, 13)))
        launcher = recovery.launcher(module, setup, parity)
        compile(launcher, "cpu", "exec")
        self.assertIn("assert available >= required", launcher)
        self.assertIn(
            "predecessor='hung-group03-shard13-recovery-20261027-v1',datasets=[]", launcher
        )
        runtime = launcher[launcher.rindex("\nassert status('hung-matched-group03-recovery") :]
        self.assertNotIn("relay(MODULE_SOURCE", runtime)
        self.assertEqual(runtime.count("\nsubmit("), 2)
