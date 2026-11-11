"""Check paired branch isolation and symmetric/restricted coefficient steps."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.issue99_decision_probe import ProbeRunner


class FakeBranch:
    def __init__(self):
        self.weight = 0.0

    def snapshot(self):
        return {"weight": self.weight}

    def clone(self, **kwargs):
        return FakeBranch()

    def update(self, record, *, weight, **kwargs):
        self.weight = weight
        return []

    def predict(self, record, **kwargs):
        return [self.weight] * 24


class DecisionProbeTests(unittest.TestCase):
    def test_branches_share_start_and_only_selected_step_changes_parent(self):
        runner = object.__new__(ProbeRunner)
        runner.branch = FakeBranch()
        runner.device = "cpu"
        runner.training = SimpleNamespace(learning_rate=0.001)
        runner.rule = SimpleNamespace(upper_bound=2.0)
        runner.replay = SimpleNamespace(stop=10, forecast=lambda _: {})
        runner.observations = []

        class Stamp(int):
            def isoformat(self):
                return "2022-12-05"

        decision = {"lambda_before": 1.0, "lambda_after": 1.25}

        def arrivals(instance, as_of, events):
            import ev_runner.continuous as module

            module.decide()
            instance.branch.update({"origin": "2022-12-04"}, weight=1.25)

        with (
            patch("ev_runner.continuous.ContinuousRunner._arrivals", arrivals),
            patch("ev_runner.continuous.decide", return_value=decision),
        ):
            runner._arrivals(Stamp(1), [])
        self.assertEqual(runner.branch.weight, 1.25)
        row = runner.observations[0]
        self.assertEqual(row["predictions_scaled"]["hold"], [1.0] * 24)
        self.assertEqual(row["predictions_scaled"]["follow"], [1.25] * 24)
        self.assertEqual(row["predictions_scaled"]["reverse"], [0.75] * 24)
        self.assertFalse(row["asymmetric_projection"])


if __name__ == "__main__":
    unittest.main()
