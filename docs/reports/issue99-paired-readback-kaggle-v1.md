# Issue #99 paired comparison: Kaggle readback addendum

This addendum records a direct read of the saved comparison's mounted output in a [Kaggle CPU notebook](https://www.kaggle.com/code/hungluongduc/issue99-protocol-v2-paired-readback-v1?scriptVersionId=367837806), saved Version 1, run `367837806`. It supplements the [protocol v2 comparison report](issue99-paired-comparison-protocol-v2.md). The original comparison ran in [Kaggle Version 1](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2), run `367824175`.

The mounted `verification.json` reported schema `issue99-paired-verification-v1`, protocol SHA-256 `f104d8809e04d0cde7d8982efd8146788f32c3c9a1c561ee9309891e6b040eb0`, and 60 coverage entries. Its SHA-256 was `c3038079cd65f575851dfd53be139017c6ad95aad087d7a3817dcd34a3d6bfed`, matching the saved comparison log. The [readback script](../../tools/issue99_kaggle_readback_v2.py), SHA-256 `f7cbb5ebdd570e5e552beaab48221743985f3f34ae00aba8cfc3d4dcd05885bc`, checked the saved code, Source checkpoints, input identity, job receipts, event/commit hashes, 28/28 Evaluation origins, and the saved forecast vectors against arrived labels. It independently recomputed cell metrics within Kaggle and matched the saved verification. The readback returned `PASS`, 60 verified jobs, receipt index SHA-256 `a61d43f9e48512ddb5c7d7b62dd2b3eccc2ef267817636460ca45561072bb696`, and output JSON SHA-256 `d34af73570dce903d99b6d8961d3f11187e88f7b6293be5f280be4f8b4e2a0d6`. The output has not been downloaded, so this is platform-side verification rather than a local byte audit.

## Forecast error readback

Each target value below is the mean of the three Source10 seed RMSE values in kWh. The macro row is the equal-weight mean of the four target RMSE values, calculated from the readback values; it is a mean of RMSEs, **not** the square root of a pooled mean squared error. The verifier does not emit a macro RMSE field.

| Target | λ=0 | Fixed λ=0.5634538227695682 | Old discrete | Continuous Adam | Frozen λ=0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1153 | 8.872708 | 8.723138 | 8.797301 | 8.953572 | 8.957767 |
| 1405 | 8.076565 | 7.618567 | 7.832275 | 8.044155 | 8.044142 |
| 1693 | 3.558112 | 3.832320 | 3.757060 | 3.754477 | 3.711192 |
| 2152 | 7.632309 | 7.524998 | 7.561131 | 7.562798 | 7.561131 |
| **Equal-target mean** | **7.034924** | **6.924756** | **6.986942** | **7.078751** | **7.068558** |

The readback's equal-target macro MAEs were λ=0 `5.077389167412713`, Fixed `4.941431498059513`, old discrete `4.972350274324078`, continuous Adam `5.0708594517889924`, and frozen λ=0.1 `5.05317344024457` kWh, matching the saved verification. Fixed had the lowest macro MAE and the lowest equal-target mean RMSE in this run. The script also recomputed all per-seed paired MAE differences against λ=0 and matched the saved verification; those individual values have not been transcribed here from the saved readback JSON.

## Measured execution cost

The readback aggregated each original comparison run's recorded invocation wall time. Every logical cell was executed once; none reused a saved run. These seconds describe the 60 GPU comparison executions, not the separate CPU readback notebook, whose saved viewer reported approximately 16 minutes 40 seconds.

| Method | Executions | Reused cells | Sum of recorded run wall time (s) |
| --- | ---: | ---: | ---: |
| λ=0 | 12 | 0 | 104.107519 |
| Fixed | 12 | 0 | 94.564363 |
| Old discrete | 12 | 0 | 107.738137 |
| Continuous Adam | 12 | 0 | 212.988075 |
| Frozen λ=0.1 | 12 | 0 | 95.879752 |

Continuous Adam consumed about 2.25 times Fixed's summed run wall time in this execution (`212.988075 / 94.564363`); this is an observed cost ratio, not a hardware-independent complexity estimate. The original Kaggle comparison version took about 777.4 seconds overall, including work beyond these recorded run invocations.

The registered Evaluation window had 28 scored origins in each of the 60 target × seed × method cells. This Development comparison is exploratory because the cohort and historical aggregate outcomes had prior exposure. It is not an untouched test. The separate [PR #102](https://github.com/HungLD9505/adaptive-retention-ev/pull/102) uses a different temporal split, search domain, and controller settings; its results must not be pooled with these values. PR #102 reports macro MAE λ=0 `4.868597`, Fixed `4.803054`, old discrete `4.798259`, and continuous `4.806223` kWh under its own protocol. Neither protocol reports an aggregate MAE advantage for the continuous controller; the absolute MAEs across protocols are not directly comparable.

## Next steps

1. Obtain the saved comparison archive when transfer is available. Verify its bytes and manifest locally, then independently recompute forecast metrics and causal coverage against the recorded labels. The Kaggle readback is a complete platform-side check; local possession and byte verification remain outstanding.
2. Transcribe or publish the saved readback's per-seed paired differences, GPU memory peaks, and cost components if a finer cost analysis is needed. The saved readback JSON contains these fields; this report records the verified aggregate and invocation wall time only.
3. Present PR #100 and PR #102 as two exploratory protocols with their distinct dates, searches, controller settings, and artifact checks. Resolve their branch overlap deliberately; do not pool their 60-cell matrices or merge the branches as if they were one experiment.
4. Update PR #100 with this evidence and limitations. Keep issue #99 open until the remaining artifact and repository review requirements are satisfied.
