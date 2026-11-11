"""Deterministic one-dimensional GP/EI proposals and bounded sensitivity design."""

import math
from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class FixedSearchConfig:
    positive_lower: float
    positive_upper: float
    maximum_upper: float
    expansion_factor: float
    boundary_fraction: float
    maximum_expansions: int
    bo_trials: int
    initial_lambdas: tuple[float, ...]
    sensitivity_points: int
    acquisition_grid_points: int
    kernel_length: float
    signal_std: float
    noise_std: float
    expected_improvement_jitter: float

    def __post_init__(self) -> None:
        positive = (
            self.positive_lower,
            self.positive_upper,
            self.maximum_upper,
            self.expansion_factor,
            self.kernel_length,
            self.signal_std,
            self.noise_std,
        )
        if not all(math.isfinite(value) and value > 0 for value in positive):
            raise ValueError("Search scales and positive domain must be finite positive")
        if not self.positive_lower < self.positive_upper <= self.maximum_upper:
            raise ValueError("Invalid positive search domain")
        if self.expansion_factor <= 1 or not 0 < self.boundary_fraction < 1:
            raise ValueError("Invalid boundary expansion rule")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < minimum
            for value, minimum in (
                (self.maximum_expansions, 0),
                (self.bo_trials, 1),
                (self.sensitivity_points, 2),
                (self.acquisition_grid_points, 16),
            )
        ):
            raise ValueError("Invalid finite search budget")
        if (
            not self.initial_lambdas
            or len(self.initial_lambdas) > self.bo_trials
            or any(
                not math.isfinite(value) or not self.positive_lower <= value <= self.positive_upper
                for value in self.initial_lambdas
            )
            or len(set(self.initial_lambdas)) != len(self.initial_lambdas)
        ):
            raise ValueError("Initial lambda design must be unique and inside domain")
        if (
            not math.isfinite(self.expected_improvement_jitter)
            or self.expected_improvement_jitter < 0
        ):
            raise ValueError("Invalid EI jitter")


def log_coordinate(value: float) -> float:
    if value <= 0 or not math.isfinite(value):
        raise ValueError("GP uses positive lambda only; evaluate zero separately")
    return math.log(value)


def sensitivity_design(config: FixedSearchConfig, upper: float) -> list[float]:
    """A declared geometric coverage grid, independent of observed scores."""
    if not config.positive_lower < upper <= config.maximum_upper:
        raise ValueError("Invalid sensitivity upper bound")
    lo, hi = math.log(config.positive_lower), math.log(upper)
    return [
        math.exp(lo + (hi - lo) * index / (config.sensitivity_points - 1))
        for index in range(config.sensitivity_points)
    ]


def expanded_upper(
    config: FixedSearchConfig,
    current_upper: float,
    expansions_used: int,
    observations: list[tuple[float, float]],
) -> float:
    """Expand only when the measured incumbent is within the registered upper band."""
    if not config.positive_upper <= current_upper <= config.maximum_upper:
        raise ValueError("Current upper bound outside registered domain")
    if expansions_used < 0:
        raise ValueError("Negative expansion count")
    if any(not math.isfinite(weight) or not math.isfinite(score) for weight, score in observations):
        raise ValueError("Nonfinite measured observation")
    if not observations or expansions_used >= config.maximum_expansions:
        return current_upper
    eligible = [(weight, score) for weight, score in observations if weight > 0]
    if not eligible:
        return current_upper
    incumbent = min(eligible, key=lambda pair: (pair[1], pair[0]))[0]
    if incumbent < current_upper * (1 - config.boundary_fraction):
        return current_upper
    return min(config.maximum_upper, current_upper * config.expansion_factor)


def expected_improvement(
    candidates: torch.Tensor,
    observations: list[tuple[float, float]],
    config: FixedSearchConfig,
) -> torch.Tensor:
    """GP posterior EI for minimization, with fixed preregistered RBF/noise settings."""
    if not observations:
        raise ValueError("EI requires actual positive-lambda observations")
    if any(weight <= 0 or not math.isfinite(score) for weight, score in observations):
        raise ValueError("EI cannot consume zero, null or nonfinite trials")
    x = torch.tensor([log_coordinate(weight) for weight, _ in observations], dtype=torch.float64)
    y = torch.tensor([score for _, score in observations], dtype=torch.float64)
    if candidates.dtype != torch.float64 or candidates.ndim != 1:
        raise ValueError("Candidate coordinates must be float64 vector")
    length = config.kernel_length
    signal2 = config.signal_std**2
    pair_distance = (x[:, None] - x[None, :]) / length
    kernel = signal2 * torch.exp(-0.5 * pair_distance.square())
    kernel.diagonal().add_(config.noise_std**2)
    factor = torch.linalg.cholesky(kernel)
    center = y.mean()
    alpha = torch.cholesky_solve((y - center).unsqueeze(1), factor).squeeze(1)
    cross = signal2 * torch.exp(-0.5 * ((x[:, None] - candidates[None, :]) / length).square())
    mean = center + cross.T @ alpha
    solved = torch.linalg.solve_triangular(factor, cross, upper=False)
    variance = (signal2 - solved.square().sum(dim=0)).clamp_min(0)
    std = variance.sqrt()
    improvement = y.min() - mean - config.expected_improvement_jitter
    z = improvement / std.clamp_min(1e-15)
    normal_cdf = 0.5 * (1 + torch.erf(z / math.sqrt(2)))
    normal_pdf = torch.exp(-0.5 * z.square()) / math.sqrt(2 * math.pi)
    ei = improvement * normal_cdf + std * normal_pdf
    return torch.where(std > 1e-15, ei.clamp_min(0), improvement.clamp_min(0))


def propose_lambda(
    config: FixedSearchConfig,
    current_upper: float,
    trials: list[tuple[float, float | None]],
) -> tuple[float, str]:
    """Return the next predesign or GP/EI real-valued proposal, never an old trial."""
    observed = {weight for weight, _ in trials}
    for weight in config.initial_lambdas:
        if weight not in observed:
            return weight, "initial"
    if len(trials) >= config.bo_trials:
        raise StopIteration("BO trial budget exhausted")
    observations = [(weight, score) for weight, score in trials if score is not None]
    if not observations:
        raise ValueError("No finite initial observation; BO cannot propose")
    lo, hi = math.log(config.positive_lower), math.log(current_upper)
    grid = torch.linspace(lo, hi, config.acquisition_grid_points, dtype=torch.float64)
    trial_grid = [math.exp(value.item()) for value in grid]
    allowed = [
        index
        for index, weight in enumerate(trial_grid)
        if all(not math.isclose(weight, prior, rel_tol=1e-10, abs_tol=0) for prior in observed)
    ]
    if not allowed:
        raise StopIteration("Finite acquisition grid exhausted")
    scores = expected_improvement(grid, observations, config)
    index = max(allowed, key=lambda position: (scores[position].item(), -position))
    return min(current_upper, max(config.positive_lower, trial_grid[index])), "bo_ei"
