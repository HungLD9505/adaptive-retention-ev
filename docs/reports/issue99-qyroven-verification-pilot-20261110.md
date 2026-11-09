# Issue #99 independent verification and pilot handoff — 10 November 2026

This checkpoint verifies the implementation and measures coefficient movement. It is not a Fixed search result, a selected controller, or evidence of improved forecasting.

## Code and independent checks

Reviewed implementation: Hung PR #100 at `e2633e40703dfa127fd802c536e0ae648e357461`.
The independent fix in PR #101, commit `96cd96e23194475a0cb9c8fee92cff09f6463975`, replaces 18 temporary-directory uses that assumed ignored `.cache` existed. No method, numerical fixture, or scientific result was changed.

On a clean committed checkout with Python 3.12.13 and PyTorch 2.11.0 CPU:

- Root suite: 928 tests passed, two CUDA skips.
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

## Scientific boundary

Keep the existing loss unchanged: normalized forecast MAE plus lambda times the dimensionwise normalized latent MSE, with the frozen Source encoder and Source-derived scales. The new update differentiates forecast MAE on arrived, untrained V through a virtual Adam step on older A, then projects lambda to its registered interval. It does not modify the GRU architecture or inherit a confidence guarantee from the historical bootstrap controller.

The draft protocol remains unlocked. Scored BO, sensitivity regime claims, and method selection require the finite measured search/controller settings, chronological objective boundary, coverage gate, and peer review. Prior Development exposure makes future outcomes exploratory. No favorable model ranking or optimal lambda interval is established here.
