"""Confidence-Based Adaptive Retention Controller.

Follows Report 1 Section 6 & Issue #41:
- Candidate levels Lambda = {0, lambda_low, lambda_high}, 0 < lambda_low < lambda_high.
- Initial 14-day evaluation blocks.
- Prequential scoring: paired daily normalized MAE improvement d_b^{j,a} = ell_b^a - ell_b^j.
- Valid day gate: B complete days (all 24 labels present), requiring B >= B_min.
- Day-block bootstrap one-sided Lower Confidence Bound (LCB) with confidence level (1 - alpha).
- Strict qualification condition: LCB > delta.
- Multiple-challenger resolution: largest qualifying LCB -> nearest current lambda -> fixed order.
- Winner carry: winning candidate checkpoint/optimizer is carried forward (never reset on keep).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class CandidateConfig:
    """Configuration for a retention candidate."""

    candidate_id: str
    lambda_val: float


@dataclass
class DailyScoreRecord:
    """Recorded forecast errors for a single day across candidates."""

    day_index: int
    active_id: str
    is_valid_day: bool  # True only if all 24 labels were present and scored
    candidate_maes: Dict[str, float] = field(default_factory=dict)


@dataclass
class ControllerDecision:
    """Decision record at the end of an evaluation block."""

    block_index: int
    initial_active_id: str
    initial_lambda: float
    selected_id: str
    selected_lambda: float
    decision_type: Literal["keep", "switch"]
    valid_days_count: int
    required_min_days: int
    challenger_stats: Dict[str, Dict[str, Any]]
    selection_reason: str


def compute_day_block_bootstrap_lcb(
    differences: np.ndarray,
    alpha: float = 0.05,
    n_resamples: int = 1000,
    segment_length: int = 1,
    random_seed: Optional[int] = None,
) -> float:
    """Compute one-sided Lower Confidence Bound (LCB) using day-block bootstrap.

    d = ell_active - ell_challenger. A positive difference indicates challenger improvement.
    The one-sided (1 - alpha) LCB satisfies P(mean_diff >= LCB) ~ 1 - alpha.
    On the bootstrap distribution of the mean, this corresponds to the alpha-quantile:
    LCB = quantile(boot_means, alpha).

    Parameters:
        differences: 1D array of daily differences for B valid days.
        alpha: significance level for one-sided bound (e.g. 0.05 for 95% confidence).
        n_resamples: number of bootstrap replicates.
        segment_length: length of contiguous block of days to preserve serial correlation.
        random_seed: seed for deterministic reproducibility.
    """
    b = len(differences)
    if b == 0:
        return float("-inf")

    rng = np.random.default_rng(random_seed)

    if segment_length <= 1 or b <= 1:
        # Standard day bootstrap
        indices = rng.integers(0, b, size=(n_resamples, b))
        boot_samples = differences[indices]
        boot_means = np.mean(boot_samples, axis=1)
    else:
        # Block bootstrap with contiguous segments of length L
        seg_len = min(segment_length, b)
        num_blocks = int(np.ceil(b / seg_len))
        boot_means = np.empty(n_resamples, dtype=np.float64)

        max_start = b - seg_len + 1
        for i in range(n_resamples):
            starts = rng.integers(0, max_start, size=num_blocks)
            sample_blocks = [differences[s : s + seg_len] for s in starts]
            sample = np.concatenate(sample_blocks)[:b]
            boot_means[i] = np.mean(sample)

    return float(np.quantile(boot_means, alpha))


class AdaptiveRetentionController:
    """Adaptive Retention Controller governing candidate levels and block switches."""

    def __init__(
        self,
        lambda_low: float = 0.1,
        lambda_high: float = 1.0,
        initial_lambda: float = 0.1,
        block_size: int = 14,
        b_min: int = 10,
        delta: float = 0.0,
        alpha: float = 0.05,
        use_bonferroni: bool = True,
        bootstrap_resamples: int = 1000,
        bootstrap_segment_length: int = 1,
        seed: int = 42,
    ) -> None:
        """Initialize controller.

        Parameters:
            lambda_low: positive lower retention level (0 < lambda_low < lambda_high).
            lambda_high: positive higher retention level.
            initial_lambda: starting retention level in {0, lambda_low, lambda_high}.
            block_size: number of days per evaluation block.
            b_min: minimum complete days required to consider switching.
            delta: minimum required strict improvement on normalized MAE scale (LCB > delta).
            alpha: one-sided significance level.
            use_bonferroni: whether to use alpha/2 for two-challenger testing.
            bootstrap_resamples: number of bootstrap resamples.
            bootstrap_segment_length: block bootstrap segment length (default 1).
            seed: master seed for bootstrap randomness.
        """
        if not (0.0 < lambda_low < lambda_high):
            raise ValueError(
                f"Levels must satisfy 0 < lambda_low < lambda_high: got {lambda_low}, {lambda_high}"
            )
        self.levels: List[float] = [0.0, float(lambda_low), float(lambda_high)]
        if initial_lambda not in self.levels:
            raise ValueError(f"initial_lambda {initial_lambda} must be in {self.levels}")

        self.block_size = block_size
        self.b_min = b_min
        self.delta = delta
        self.alpha = alpha
        self.use_bonferroni = use_bonferroni
        self.bootstrap_resamples = bootstrap_resamples
        self.bootstrap_segment_length = bootstrap_segment_length
        self.seed = seed

        self.active_lambda = initial_lambda
        self.active_id = self._id_for_lambda(initial_lambda)
        self.current_block: int = 0
        self.block_records: List[DailyScoreRecord] = []
        self.decision_history: List[ControllerDecision] = []

    def _id_for_lambda(self, lam: float) -> str:
        if lam == 0.0:
            return "cand_0"
        if lam == self.levels[1]:
            return "cand_low"
        if lam == self.levels[2]:
            return "cand_high"
        return f"cand_{lam}"

    def get_candidate_configs(self) -> List[CandidateConfig]:
        """Return configs for the three candidate levels {0, lambda_low, lambda_high}."""
        return [
            CandidateConfig(candidate_id="cand_0", lambda_val=0.0),
            CandidateConfig(candidate_id="cand_low", lambda_val=self.levels[1]),
            CandidateConfig(candidate_id="cand_high", lambda_val=self.levels[2]),
        ]

    def record_day_scores(
        self,
        day_index: int,
        is_valid_day: bool,
        candidate_maes: Dict[str, float],
    ) -> None:
        """Record the prequential forecast MAE for all candidates on day index."""
        rec = DailyScoreRecord(
            day_index=day_index,
            active_id=self.active_id,
            is_valid_day=is_valid_day,
            candidate_maes=dict(candidate_maes),
        )
        self.block_records.append(rec)

    def evaluate_block_decision(self, block_index: int) -> ControllerDecision:
        """Evaluate block completion and decide whether to switch retention level.

        Returns:
            ControllerDecision detailing the outcome, LCB values, and selection rationale.
        """
        # Filter records for complete days with valid labels
        valid_records = [r for r in self.block_records if r.is_valid_day]
        b_count = len(valid_records)

        challenger_stats: Dict[str, Dict[str, Any]] = {}
        candidate_configs = {c.candidate_id: c.lambda_val for c in self.get_candidate_configs()}
        challenger_ids = [cid for cid in candidate_configs if cid != self.active_id]

        # Case 1: Insufficient valid days
        if b_count < self.b_min:
            reason = (
                f"Insufficient complete days (B={b_count} < B_min={self.b_min}). "
                f"Retaining active {self.active_id} (lambda={self.active_lambda})."
            )
            for cid in challenger_ids:
                challenger_stats[cid] = {
                    "lambda": candidate_configs[cid],
                    "mean_diff": 0.0,
                    "lcb": float("-inf"),
                    "qualifies": False,
                    "b_count": b_count,
                }
            decision = ControllerDecision(
                block_index=block_index,
                initial_active_id=self.active_id,
                initial_lambda=self.active_lambda,
                selected_id=self.active_id,
                selected_lambda=self.active_lambda,
                decision_type="keep",
                valid_days_count=b_count,
                required_min_days=self.b_min,
                challenger_stats=challenger_stats,
                selection_reason=reason,
            )
            self.decision_history.append(decision)
            self.block_records.clear()
            self.current_block += 1
            return decision

        # Compute paired differences and bootstrap LCB for each challenger
        # Alpha adjustment for 2 challengers if enabled
        eff_alpha = (self.alpha / len(challenger_ids)) if self.use_bonferroni else self.alpha

        qualifying_challengers: List[Tuple[str, float, float]] = []  # (cid, lcb, lambda)

        for cid in challenger_ids:
            # d_b = mae_active - mae_challenger (positive => challenger is better)
            diffs = np.array(
                [r.candidate_maes[self.active_id] - r.candidate_maes[cid] for r in valid_records],
                dtype=np.float64,
            )
            mean_diff = float(np.mean(diffs))

            # Deterministic bootstrap seed per block and challenger
            boot_seed = (
                self.seed + block_index * 31 + int(candidate_configs[cid] * 1000)
            ) & 0xFFFFFFFF
            lcb = compute_day_block_bootstrap_lcb(
                diffs,
                alpha=eff_alpha,
                n_resamples=self.bootstrap_resamples,
                segment_length=self.bootstrap_segment_length,
                random_seed=boot_seed,
            )

            # Strict qualification condition: LCB > delta
            qualifies = bool(lcb > self.delta)
            if qualifies:
                qualifying_challengers.append((cid, lcb, candidate_configs[cid]))

            challenger_stats[cid] = {
                "lambda": candidate_configs[cid],
                "mean_diff": mean_diff,
                "lcb": lcb,
                "qualifies": qualifies,
                "b_count": b_count,
            }

        # Case 2: No challenger qualifies -> Keep active
        if not qualifying_challengers:
            reason = (
                f"No challenger satisfied strict LCB > delta ({self.delta}). "
                f"Retaining active {self.active_id} (lambda={self.active_lambda})."
            )
            decision = ControllerDecision(
                block_index=block_index,
                initial_active_id=self.active_id,
                initial_lambda=self.active_lambda,
                selected_id=self.active_id,
                selected_lambda=self.active_lambda,
                decision_type="keep",
                valid_days_count=b_count,
                required_min_days=self.b_min,
                challenger_stats=challenger_stats,
                selection_reason=reason,
            )
            self.decision_history.append(decision)
            self.block_records.clear()
            self.current_block += 1
            return decision

        # Case 3: Multiple or single qualifying challenger
        # Tie-breaking rules from Report 1 & Acceptance Criteria:
        # 1. Largest LCB
        # 2. Nearest lambda to current active lambda: abs(lambda - active_lambda)
        # 3. Fixed order: smaller lambda first
        def sort_key(item: Tuple[str, float, float]) -> Tuple[float, float, float]:
            cid, lcb, lam = item
            # Negative lcb for descending order
            # Distance to active lambda for ascending order
            # lambda value for fixed order
            dist = abs(lam - self.active_lambda)
            return (-round(lcb, 6), round(dist, 6), lam)

        qualifying_challengers.sort(key=sort_key)
        winner_id, winner_lcb, winner_lam = qualifying_challengers[0]

        reason = (
            f"Challenger {winner_id} (lambda={winner_lam}) won with LCB={winner_lcb:.6f} > {self.delta}. "
            f"Switching from {self.active_id} to {winner_id}."
        )

        decision = ControllerDecision(
            block_index=block_index,
            initial_active_id=self.active_id,
            initial_lambda=self.active_lambda,
            selected_id=winner_id,
            selected_lambda=winner_lam,
            decision_type="switch",
            valid_days_count=b_count,
            required_min_days=self.b_min,
            challenger_stats=challenger_stats,
            selection_reason=reason,
        )

        # Update active state for next block
        self.active_id = winner_id
        self.active_lambda = winner_lam
        self.decision_history.append(decision)
        self.block_records.clear()
        self.current_block += 1
        return decision
