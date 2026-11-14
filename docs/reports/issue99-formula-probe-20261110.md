# Issue #99: small local lambda and retention formula probe (10 November 2026)

## Scope and formulas

This is an exploratory **Calibration-only** diagnostic, separate from the scored #99 protocols and PR #102. It does not modify the original loss, controller, checkpoints, or historical runs. The existing forecast objective is normalized 24-hour MAE. Its retention is `R_MSE = mean(u²)` with `u = (z_target - stopgrad(z_source)) / (stopgrad(source_scale) + epsilon)`. Fixed uses `lambda_F = 0.5634538227695682`, selected in the earlier protocol-v2 Calibration search.

Two changes were tested separately:

1. **Anchored lambda**, with the original retention: compute the existing causal A/V one-step Adam hypergradient `g_t`, then set `d_t = clip(-30 g_t, -0.05, 0.05)` and `lambda_(t+1) = clip(lambda_t + d_t - 0.10(lambda_t - lambda_F), lambda_F - 0.25, lambda_F + 0.25)`, also respecting the original `[0, 8]` range. Start at `lambda_F`; A/V=`2/1`. The step cap, anchor, and trust interval are design hypotheses, not tuned or validated settings.
2. **Pseudo-Huber retention**, with lambda held at `lambda_F`: `R_PH = mean[2 delta² (sqrt(1 + (u/delta)²) - 1)]`, `delta=1`. It agrees with `u²` near zero and bounds the gradient of each large residual. The scale, Source10 reference, forecast MAE, and real Adam training remain the same. This is a method change and would require a newly versioned protocol and lambda recalibration before a scored study.

The probe used the authenticated 14-day input and Source10 checkpoints, targets 2152 and 1693, seeds 42 and 43, first 22 replay ticks, and the 19 registered Calibration origins per target. Each arm used a fresh target clone and Adam state. All 12 runs completed; all 228 requested Calibration scores were present and unique (76 per arm). The Fixed baselines exactly match the four corresponding cells from the earlier local v3 probe. No Evaluation or Final score was inspected or used for this decision.

## Observed Calibration MAE

Differences are candidate minus paired Fixed; negative is better. Units are kWh.

| Target | Seeds | Fixed mean | Anchored lambda difference | Pseudo-Huber difference |
| --- | ---: | ---: | ---: | ---: |
| 2152 | 42, 43 | 6.413747 | +0.024675 | +0.024090 |
| 1693 | 42, 43 | 2.309726 | -0.013533 | -0.015679 |
| **Equal-cell macro** | **4 cells** | **4.361737** | **+0.005571** | **+0.004205** |

Anchored lambda made 19 decisions per run (76 total), with no trust-bound hit. It moved within approximately `[0.4266, 0.6957]` across the four runs. The saved invocation wall seconds sum to 21.96 for Fixed, 32.83 for anchored lambda, and 15.41 for pseudo-Huber. These sequential timings include first-run warm-up and are not a controlled speed comparison. PyTorch emitted a non-contiguous GRU weight performance warning; no run failed.

**Conclusion:** Neither formula improves the small paired Calibration macro. Both hurt target 2152. These four cells reuse a previously explored Calibration window and cannot establish generalization or an independent significance claim. Do not promote either formula to Kaggle or replace the supported Fixed baseline from this probe. A future formula study needs a fresh versioned protocol, a genuinely uninspected selection window if one exists, per-target harm limits, full cohort, and retained run/code hashes. If no untouched Development window exists, label it exploratory.

## Reproduction and artifact identity

- Worktree: `D:\Đồ Án\.cache\issue99-retention-audit`; branch `feat/continuous-retention-99`.
- Probe script: `.cache/issue99-formula-probe-v1.py`. The executed file had SHA-256 `2a4e67f440fe237174d51a95b7fed0129b43b268c889969cff41afec71d87eea`. Ruff subsequently changed only imports and formatting; the current local file has SHA-256 `d098fd785a3383dadbd2485c094dbb7eb2353c3d1f570ca96dad0800af4d815f`. The exact executed script bytes were not preserved, so the run relies on the recorded formula and output events for audit.
- Output directory: `.cache/issue99-formula-probe-v1/`; twelve distinct run directories and `summary.json`, SHA-256 `1ef2a654ccaec8d41640d06f46bf96f9e56e6d80cd63210e44e790571545513b`. These ignored artifacts are local and are not uploaded to GitHub.
- Inputs: `.cache/issue99-comparison-stage-local-v2-preview/inputs`, bound to the manifest SHA-256 in `configs/issue99-protocol-locked-v2.json`; Source10 checkpoints: `.cache/issue99-comparison-stage-local-v2-preview/sources/seed{42,43}/epoch-10.pt`, bound to the same protocol's checkpoint hashes. The probe called the repository loader for each run.
- The script temporarily patches the imported retention function or controller decision function in memory. Its run IDs and repository code identity alone do **not** bind these monkeypatches; the script hash and this report are required to interpret the diagnostic. No formal resume or hash-binding claim is made for the new formulas.

Commands: `python -m py_compile .cache/issue99-formula-probe-v1.py`; `PYTHONPATH=. python .cache/issue99-formula-probe-v1.py` (PowerShell environment syntax); independent Python aggregation of `summary.json`; comparison of Fixed cell MAEs against `.cache/issue99-controller-probe-v3/summary.json`. No Kaggle run was submitted for these variants.
