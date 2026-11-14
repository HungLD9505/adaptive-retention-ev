# Issue #99: proposed delayed-feedback lambda controller (10 November 2026)

## Status and objective

This is an **untested method proposal**, not a change to the scored #99 protocol or evidence of improved MAE. Keep the Report 1 forecast MAE, Source-scaled latent MSE retention, frozen Source10 reference, and real Adam target update. The current supported Fixed coefficient is `lambda_F = 0.5634538227695682` for the PR #100 exploratory protocol; a different protocol must use its own calibrated Fixed anchor.

The existing controller differentiates a virtual Adam update on older arrived A labels against newer arrived V labels, but the real update trains V and affects later forecasts. Its A→V hypergradient is therefore an indirect proxy for the V→future decision. In PR #100 the small meta step barely moved lambda, while more aggressive local changes moved it without a stable MAE gain. See `issue99-controller-followup-20261110.md` and `issue99-formula-probe-20261110.md`. The following controller measures the sensitivity of a **forecast actually issued after a real update** to the lambda used for that update. It uses the general hypergradient-through-optimizer idea described by [Baydin et al., ICLR 2018](https://mlanthology.org/iclr/2018/baydin2018iclr-online/); the delayed pairing, gate, and anchor here are specific new hypotheses for this repository.

## Causal observation and hypergradient

At a daily tick, the runner first processes complete labels and performs real target updates, then issues that tick's forecast. If a newly arrived complete day `V_t` causes the **last** real Adam update before a forecast `W_t` is issued, save the pre-update model parameters `theta_t^-`, Adam moments/step counters `s_t^-`, the V training record, lambda used, and the W input/forecast hash. Skip a tick with no update or no forecast. If multiple labels arrive in one tick, retain the snapshot before the last update; the earlier updates are already included in that snapshot.

When W's complete label arrives, **before** training on W, replay the V update virtually from that snapshot and compute

```text
theta_t^+(lambda) = VirtualAdam(theta_t^-, s_t^-,
                                  MAE_V(theta_t^-) + lambda * R_V(theta_t^-))
g_t = d MAE_W(f(theta_t^+(lambda), x_W), y_W) / d lambda
      evaluated at lambda = lambda_used_for_V.
```

The virtual forecast at the recorded lambda must reproduce the saved W forecast within the defined deterministic tolerance and match its origin/hash binding. Otherwise the pair is invalid and no lambda update is made. Require `origin(V) < origin(W)`, V's label available at its real update, W's label unavailable when forecast issued and complete when `g_t` is computed, and no intervening real update between the saved V snapshot and W issuance. Never train on W before computing `g_t`. This makes `g_t` the one-step sensitivity of an observed post-update forecast, rather than a claim about a future unseen label. It still cannot guarantee that the same gradient sign will help later days.

## One bounded update rule

Keep the last five valid delayed hypergradients. When five are available, let `m_t = median(g_(t-4),...,g_t)`. Set `a_t=1` only if at least four of the five have the same nonzero sign as `m_t`; otherwise set `a_t=0`. With fewer than five valid gradients, set `a_t=0`. Then use

```text
lambda_(t+1) = clip(
    lambda_F + rho * (lambda_t - lambda_F)
             - a_t * clip(eta * m_t, -d, d),
    max(0, lambda_F - Delta), min(U, lambda_F + Delta)
)
lambda_0 = lambda_F.
```

`rho<1` returns lambda gradually toward the supported Fixed anchor when the delayed signal is absent or inconsistent. The median and 4/5 sign gate reduce reactions to one noisy day. `d` caps a single movement; `Delta` caps total departure from Fixed; `U` is the existing nonnegative protocol limit. Invalid or nonfinite gradients produce an explicit skip event and the anchor-only update, never a silent NaN. A bounded pilot could start with `rho=0.9`, `eta=10`, `d=0.02`, `Delta=0.25`, `U=8`, giving the tentative interval `[0.31345,0.81345]`. **These values are engineering starting points, not empirically selected or proven optimal.** Register them before any scored run; select adjustments using Calibration only.

This rule preserves a null action: with no reliable delayed feedback it behaves as Fixed, apart from gradual reversion after a prior deviation. It adds one virtual Adam step and second-order differentiation per valid delayed observation, plus a retained pre-update snapshot. Measure actual VRAM and wall time rather than assuming it is cheap. Save the snapshot, optimizer state, queued forecast identity, five-gradient history, lambda, and gate decisions in atomic checkpoints; bind the method version and all parameters to run/resume hashes. A resume must reproduce forecast and lambda traces exactly.

## Required small test before any scored study

1. Unit tests: finite-difference `g_t` on a small model; virtual-versus-real Adam forecast equality; forecast hash mismatch skip; late/incomplete labels; W not trained before gradient; multiple arrivals; lambda bounds; all-zero/inconsistent gradients; snapshot/resume identity; no mutation of real Adam by the virtual replay.
2. Calibration-only paired pilot: four targets × seeds 42/43/44, 19 registered origins per cell, same Source10/input/forecast loss and fresh target Adam, compared against exact Fixed and frozen-lambda controls. Log `g_t`, gate, lambda path, skipped pairs, coverage, future score, wall time and VRAM. Do not select from Evaluation or Final; those windows were previously viewed in #99.
3. Proposed promotion rule from the existing follow-up: full score coverage; macro MAE gain at least `0.05` kWh over paired Fixed; no target mean harm above `0.05` kWh; wall cost at most `2x` Fixed; finite and exactly resumable decisions. The local Calibration window has itself been explored, so even a pass is exploratory, not an independent effectiveness claim. A new scored study needs a versioned method/protocol and a genuinely uninspected assessment window.

No code or run was changed for this proposal. It does not supersede PR #100/#102 results, and the current controller has not been replaced.
