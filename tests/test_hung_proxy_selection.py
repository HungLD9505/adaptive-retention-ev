"""Independent causal and resume checks for the three Source proxy policies."""

from __future__ import annotations

import unittest

import torch

from experiments.hung_sprint2.controller import ControllerConfig
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.proxy_selection import ProxyConfig, decide_proxy_block
from experiments.hung_sprint2.retention import frozen_source_reference
from experiments.hung_sprint2.runner import LabelArrival, Origin, PrequentialRunner
from tests.test_hung_runner import binding


def controller() -> ControllerConfig:
    return ControllerConfig(
        levels=(0.0, 0.1, 0.3),
        initial_level=0.1,
        block_days=2,
        min_complete_days=1,
        delta=0.0,
        alpha=0.05,
        bootstrap_segment_days=1,
        bootstrap_resamples=11,
        seed=9,
        challenger_rule="bonferroni_two",
    )


def make_runner(rule: str, config: ProxyConfig) -> PrequentialRunner:
    torch.manual_seed(17)
    model = ForecastGRU(ModelConfig(calendar_hidden=8))
    return PrequentialRunner(
        model,
        torch.optim.Adam(model.parameters(), lr=0.01),
        frozen_source_reference(model),
        torch.ones(64),
        binding=binding(),
        controller=controller(),
        epsilon=1e-6,
        energy_scale=5.0,
        selection_rule=rule,
        proxy_config=config,
    )


def origin(index: int, load: float = 0.4, mask: float = 1.0) -> Origin:
    x = torch.zeros((1, 24, 7))
    x[:, :, 0] = load
    x[:, :, 6] = mask
    return Origin(f"proxy-{index}", index, x, torch.zeros((1, 24, 5)))


def label(index: int, value: float = 0.4) -> LabelArrival:
    return LabelArrival(
        f"proxy-{index}", True, torch.full((24,), value), torch.ones(24, dtype=torch.bool)
    )


class ProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_explicit_mapping_allows_high_drift_to_high_retention(self) -> None:
        config = ProxyConfig(0.2, 0.8, (0.0, 0.1, 0.3), 0.0, 1.0)
        result = decide_proxy_block(
            controller(),
            current_level=0.1,
            scheduled_days=2,
            values=[1.0, 1.2],
            config=config,
            rule="drift",
        )
        self.assertEqual(result.selected_level, 0.3)
        self.assertAlmostEqual(result.proxy_value, 1.1)
        with self.assertRaisesRegex(ValueError, "each candidate"):
            ProxyConfig(0.2, 0.8, (0.0, 0.0, 0.3), 0.0, 1.0).validate(controller(), "drift")

    def test_source_error_requires_arrived_label_and_late_label_cannot_revise(self) -> None:
        config = ProxyConfig(0.01, 0.02, (0.0, 0.1, 0.3))
        run = make_runner("source_error", config)
        run.forecast(origin(0))
        self.assertIsNone(run.issued[0]["proxy_value"])
        run.arrive(LabelArrival("proxy-0", False, deferred=True))
        run.forecast(origin(1))
        run.arrive(LabelArrival("proxy-1", False, deferred=True))
        first = run.finish_block()
        self.assertEqual(first.reason, "insufficient_days")
        self.assertEqual(run.proxy_costs["inference_calls"], 2)
        run.arrive(label(0))
        self.assertIsNotNone(run.issued[0]["proxy_value"])
        self.assertEqual(run.decisions[0], first)
        self.assertEqual(run.update_steps, [1, 1, 1])

    def test_drift_uses_only_present_history_and_resume_matches(self) -> None:
        config = ProxyConfig(0.2, 0.8, (0.0, 0.1, 0.3), 0.0, 1.0)
        run = make_runner("drift", config)
        first = origin(0, 0.4)
        first.x_hist[:, :12, 0] = 0.0
        first.x_hist[:, :12, 6] = 0.0
        run.forecast(first)
        self.assertAlmostEqual(run.issued[0]["proxy_value"], 0.4, places=6)
        restored = PrequentialRunner.from_state_dict(run.state_dict(), expected_binding=binding())
        for instance in (run, restored):
            instance.arrive(label(0))
            instance.forecast(origin(1, 1.0))
            instance.arrive(label(1))
        self.assertEqual(run.finish_block(), restored.finish_block())
        self.assertEqual(run.decisions[-1].selected_level, 0.1)
        self.assertEqual(restored.proxy_costs["inference_calls"], 2)

    def test_uncertainty_is_prediction_only_and_extra_cost_is_bound(self) -> None:
        run = make_runner("uncertainty", ProxyConfig(0.01, 0.05, (0.3, 0.1, 0.0)))
        run.forecast(origin(0))
        self.assertGreaterEqual(run.issued[0]["proxy_value"], 0)
        self.assertIsNone(run.issued[0]["y_scaled"])
        self.assertEqual(run.proxy_costs["inference_calls"], 1)
        state = run.state_dict()
        state["proxy_costs"]["inference_calls"] = 0
        with self.assertRaisesRegex(ValueError, "cost accounting"):
            PrequentialRunner.from_state_dict(state, expected_binding=binding())


if __name__ == "__main__":
    unittest.main()
