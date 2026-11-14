# Verified execution and interpretation

**Main outcome:** Continuous is lower than lambda0 but does not beat calibrated Fixed on the registered later objective. Continuous-minus-Fixed is +0.003169227 kWh. Continuous is lower on 3/4 selected station means, while target 2152 is worse by 0.108643820 kWh. These are descriptive paired-seed means, not significance claims. Retention also worsens target 1693 relative to lambda0 for every retained method; this adverse case is preserved.

The full-90 descriptive mean is slightly lower for Continuous than Fixed (5.052390298 vs 5.053859319 kWh), while the registered later-objective result goes the other way. The full-90 mixture includes the calibration period used for selection, so it must not replace the registered primary comparison to claim a win.

## Execution counts

- Fixed: 21 actually measured coefficients, 252 station/seed invocations.
- Selected-initialization controller scaling pilot: 12 invocations.
- Controller calibration: six registered recipes, 72 invocations.
- Comparison: 60 logical method/station/seed cells, 48 new invocations and 12 exact frozen-to-Fixed reuses.
- Total current GPU study: 384 invocations; no Source retraining. The separate twelve pre-deployment CPU gradient probes and earlier issue99 pilots are outside this timing total.
- All 90 scheduled days were replayed. Actual issued/scored coverage remains explicit; later scored days are 60/22/22/22 in target order 1405/2152/1153/1693.

## Independent verification

The downloaded archive is 264,510,116 bytes, SHA-256 `20f9e9ef62a9264209318348820fa2774f209ef2293398a94dda62e891722f6e`. All 43,397 study files, Source checkpoints and executed code archive matched the manifest/receipt. The restored fixed trial journal chain, every fixed/controller calibration report and the full five-method matrix passed independent saved-prediction/arrived-label metric and tick-commit checks.

All 384 retained checkpoints loaded on CPU; 408 GRU states loaded strictly, including the legacy controller's shadow branches, with finite model/Adam tensors. Fresh evaluation executions reproduced 672 selected calibration-prefix forecast vectors across 24 paired runs with maximum difference 0.0. The main offline suite ran 935 tests (933 passed, two CUDA-only skips); 41 issue99 preflight tests passed on T4, followed by the local cost/checkpoint tests. Both experiment suites passed (9 fixed, 12 confidence); source listing, release checks, Ruff lint/format and diff checks passed. Original all-namespace external artifact tests were not run; this study's artifacts have their own verified readback.

A newly introduced GPU fixture initially passed CPU inputs to a CUDA model. It was corrected before any scored trial. The logs preserve that failed preflight and successful repeat. Figure QA removed misleading negative autoscale ranges from nonnegative coefficient/diagnostic axes; measured values were unchanged.

The owned T4 session was terminated. Final inventory: zero active assignments, zero usage rate. Observed account balance changed from 14.89 to 14.36 CU; this rounded service balance delta is not a complete per-study billing invoice. Measured end-to-end study wall is 1037.043772 seconds; phase/invocation counters exclude provisioning, transfer, tests and earlier pilots. Historical Source pretraining and unmeasured CPU-probe elapsed costs remain unknown.

## Interpretation limits

The interval and step recipe are outcomes of the registered finite calibration rules. They are not universal optimum constants. The four-target cohort was already inspected, all stations are in one city, and the later split is exploratory. No global GRU/transfer superiority, significance, or new safety guarantee is established. Lambda0 is Source-initialized full fine-tuning, not a target-only network; issue97 remains the separate backbone/transfer study.

Daily hypergradients can have heterogeneous effects: three station means improve versus Fixed and one worsens enough to reverse the aggregate. That observation does not establish why; a claim that one-step noise or the A/V policy caused the difference would require a separate controlled experiment. No retuning was performed after viewing later-objective scores.

## Files for review

[Methods and results](paper-method-and-results.md), [full-precision method table](method-summary.csv), [paired runs](comparison-runs.csv), [fixed observed categories](fixed-regimes.csv), [controller events](controller-events.jsonl), [costs](cost-summary.json).

[Fixed sensitivity and gradients](fixed-sensitivity.png), [calendar-aligned coefficient/error trajectories](controller-trajectories.png), [method means](method-comparison.png), [evaluation invocation cost](evaluation-cost.png). PDF copies are included for export. The loss and update formulas are in the method draft; numerical intervals and coverage are in the immutable protocol lock.
