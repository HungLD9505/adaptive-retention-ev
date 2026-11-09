"""A finite artifact audit must reject corrupted numerical state."""

import unittest

import torch

from ev_models.model import ForecastGRU
from ev_runner.state import Branch, rng_state
from tools.issue99_checkpoint_audit import check_branch


class CheckpointAuditTests(unittest.TestCase):
    def test_accepts_compatible_branch_and_rejects_nan(self):
        model = ForecastGRU()
        branch = Branch(model, torch.optim.Adam(model.parameters()), rng_state()).snapshot()
        check_branch(branch)
        next(iter(branch["model"].values())).flatten()[0] = float("nan")
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            check_branch(branch)
