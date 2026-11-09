# Issue #99 independent verification and pilot handoff — 10 November 2026

This checkpoint verifies the implementation and measures coefficient movement. It is not a Fixed search result, a selected controller, or evidence of improved forecasting.

## Code and independent checks

Reviewed implementation: Hung PR #100 at `e2633e40703dfa127fd802c536e0ae648e357461`.
The independent fix in PR #101, commit `96cd96e23194475a0cb9c8fee92cff09f6463975`, replaces 18 temporary-directory uses that assumed ignored `.cache` existed. No method, numerical fixture, or scientific result was changed.

On a clean committed checkout with Python 3.12.13 and PyTorch 2.11.0 CPU:

- Root suite: 928 tests run; 926 passed and two CUDA checks skipped.
- All 36 issue99 tests passed, including a checkout without a pre-created `.cache`.
- Fixed-adaptation suite: nine passed. Confidence-controller suite: 12 passed.
- Ruff lint and format: passed, 539 files. `git diff --check`: passed.
- Source listing and release verification passed; historical external release artifacts were not freshly downloaded or authenticated by those commands.

The first full-suite attempt failed the existing clean-worktree identity check while the test fix was uncommitted. Committing the fix resolved that failure; no identity guard was disabled.

## Bounded real-input CPU pilot

The [machine-readable measurements](issue99-qyroven-cpu-pilot-v1.json) bind the exact code, input manifest and source population. All three Source10 checkpoint SHA-256 values matched the independently loaded audit. Immutable prepared input files were verified by the existing loaders. The publisher's raw archives were not freshly checked.

Twelve runs used four declared Development targets and three seeds, each stopped after ten scheduled ticks. Every run has a null scored objective. Saved pre-label forecasts were scored only after complete labels arrived to exercise the replay. Those internal diagnostics are not a comparison objective or a validation win.

Probe settings: initial lambda 1, temporary upper bound 10, meta step 0.01, two older A days, one newer untrained V day, daily meta cadence. These settings test implementation and gradient scale; **they are not selected study parameters**. The historical sweep winner at the upper endpoint 1 motivates inspecting beyond 1, but does not justify selecting 10 as the final bound.

The twelve runs issued 120 forecasts, processed 105 real Adam steps and 81 finite meta decisions. Across all decisions lambda stayed between 0.999924637511 and 1.000047835566, without projection hits. Median absolute hypergradient was 0.000314067030558.

**Verified finding:** this particular meta step produces very little movement in the inspected ten-day prefixes. **Inference:** controller step scaling needs calibration before claiming meaningful adaptation. This does not show that a larger step improves forecasting or that later days would behave identically.

The CPU pilot is separate from the planned T4 measurement. It does not authorize replacing a reviewed GPU cost comparison with CPU timings. Full pilot artifacts and the exact driver are outside Git under `runs/issue99-qyroven-cpu-pilot-matrix-20261110-v1/` in the original checkout; individual `run.json` hashes are recorded in the summary.

## Data-derived step-scale probe

A second bounded diagnostic used seed 42 on the same four targets and ten-tick prefixes. The scale rule was `eta = q * lambda_initial / median(abs(hypergradient))`, where the median came from the preceding 81 decisions. The declared conditioning probes `q = 0.01, 0.1, 1` correspond to nominal 1%, 10%, and 100% coefficient steps at that prior median. They are not asserted to be optimal or mandated by a paper. Nonlinear trajectory changes mean actual steps need not match the nominal percentages.

| Nominal fraction | Derived meta step | Observed lambda range | Projection hits |
| --- | ---: | --- | ---: |
| 0.01 | 31.840336702 | [0.741032107, 1.148288916] | 0 |
| 0.1 | 318.403367021 | [0.000000000, 4.785895995] | 2 |
| 1 | 3184.033670208 | [0.000000000, 10.000000000] | 6 |

The [per-cell probe record](issue99-qyroven-meta-scale-probe-v1.json) contains null scored objectives and exact report hashes. All 12 commit chains and 35 saved score events per fraction were checked against their saved forecasts and complete arrived labels. Separately, all 12 original pilot chains and 105 score events passed the same read-only validation.

**Verified:** magnitude calibration changes the coefficient trajectory, and the largest probe hits the temporary bounds. **Unknown:** which meta step forecasts best, whether the final interval should include these bounds, and which fixed-lambda regimes the calibration curve will support. These questions remain for the registered scored calibration; this probe did not select them.

## T4 pilot completed

A separate Colab Tesla T4 runtime authenticated the 83,570,182-byte transport payload and code archive against SHA-256 recorded before upload. A failed whole-file upload was replaced by 20 transport chunks; the reassembled bytes matched the original payload SHA-256. The existing loaders then authenticated the prepared input and all three Source10 checkpoints.

All 36 issue99 tests passed on T4, with zero skips. A complete four-target by three-seed diagnostic matrix ran ten scheduled ticks per cell, issuing 120 forecasts, processing 105 real updates, and making 81 finite meta decisions. The same diagnostic settings were used as the first CPU pilot. All scored objectives remain null.

Observed lambda range on T4: [0.999924633960, 1.000047835372], with no projection hits. The largest absolute difference in final lambda from its paired CPU probe was 1.55766309851e-08; this measured agreement does not establish general cross-platform bitwise reproducibility. The CPU and GPU Python/PyTorch versions differ, so these measurements are not a controlled hardware speed comparison.

Maximum PyTorch peak allocated memory was 88,850,432 bytes and peak reserved memory was 92,274,688 bytes. These counters do not measure total device memory use. The complete runtime, per-cell timings and archive receipt are in the [T4 pilot record](issue99-qyroven-t4-pilot-v1.json). Runtime: Python 3.13.16, PyTorch 2.14.1+cu130, CUDA 13.0, Tesla T4. A GRU weight-contiguity warning was emitted; the tests and pilot completed, and no performance optimization was introduced in response.

The result archive is 63,978,876 bytes, SHA-256 `5b40c1b3a0d3185193a517fa6ca2e4034cb6242d3115cc7ef8fbe17bac1e0af7`. Full checkpoint/event artifacts are outside Git under `runs/issue99-qyroven-t4-pilot-20261110-v1/` in the original checkout. The remote driver and transport manifest are preserved there. After download, the archive and summary hashes matched the remote receipt. All 12 downloaded tick commit chains and 105 saved-score events passed local recomputation against complete arrived labels. The owned Colab session was terminated; the final inventory reported zero active assignments and zero usage rate.

## Equations actually implemented

For a complete batch of days B, the forecast term is

$$L_F(B;\theta)=\frac{1}{24|B|}\sum_{i\in B}\sum_{j=1}^{24}|\hat y^{scaled}_{ij}(\theta)-y^{scaled}_{ij}|.$$

With frozen Source parameters theta_s and Source-derived latent scales s_k,

$$R(B;\theta)=\frac{1}{64|B|}\sum_{i\in B}\sum_{k=1}^{64}\left(\frac{h_k(x_i;\theta)-h_k(x_i;\theta_s)}{s_k+\epsilon}\right)^2,\qquad L_A=L_F(A;\theta)+\lambda R(A;\theta).$$

The denominator is divided before squaring. Fixed holds a real-valued lambda constant within its run. The proposed continuous controller uses one virtual Adam step with the current moments held fixed while differentiating the current gradient:

$$\tilde\theta_t(\lambda)=\operatorname{AdamStep}(\theta_t,m_t,v_t;\nabla_\theta L_A(\theta_t,\lambda)),\qquad \lambda_{t+1}=\Pi_{[0,U]}\left(\lambda_t-\eta\frac{\partial L_F(V;\tilde\theta_t(\lambda))}{\partial\lambda}\bigg|_{\lambda=\lambda_t}\right).$$

A contains older complete arrived days; V contains newer complete arrived days not yet consumed by real training. The outer objective contains forecast error only. The one-step regularization-hypergradient rationale follows [Luketina et al. (2016)](https://proceedings.mlr.press/v48/luketina16.pdf); the exact current-Adam implementation, A/V policy, projection and numerical treatment are study choices requiring review. Neither this paper nor the update equation supplies an optimal numerical U or eta for this dataset. The measured step-scale probes above address numerical movement only.

## Scientific boundary

Keep the existing loss unchanged: normalized forecast MAE plus lambda times the dimensionwise normalized latent MSE, with the frozen Source encoder and Source-derived scales. The new update differentiates forecast MAE on arrived, untrained V through a virtual Adam step on older A, then projects lambda to its registered interval. It does not modify the GRU architecture or inherit a confidence guarantee from the historical bootstrap controller.

The draft protocol remains unlocked. Scored BO, sensitivity regime claims, and method selection require the finite measured search/controller settings, chronological objective boundary, coverage gate, and peer review. Prior Development exposure makes future outcomes exploratory. No favorable model ranking or optimal lambda interval is established here.
