# Issue #99 paired decision diagnostic

This exploratory CPU run tests whether a controller decision improves the next issued daily forecast after the actual newly arrived-label update. All four previously inspected Development targets and Source10 seeds 42/43/44 completed. There are 294 scored paired forecasts. Following the controller beats holding its coefficient in 153 pairs. Equal-target mean follow minus hold MAE is −0.000182 kWh. This diagnostic does not establish a practically meaningful improvement.

| Target | Follow minus hold, kWh | Reverse minus hold, kWh |
| --- | ---: | ---: |
| 1405 | -0.000416 | +0.000474 |
| 2152 | +0.001140 | -0.001004 |
| 1153 | -0.000248 | +0.000240 |
| 1693 | -0.001203 | +0.000947 |

At target 2152 the mean sign favors reversing the proposed adjustment. This is evidence about the local decision on this continuous parent trajectory. It does not establish the cause of the previous later-window result or show that a reversed controller would improve a complete replay.

## Execution

The parent follows the existing #102 continuous configuration, starting at lambda 0.7984450067079901, A/V 2/1, meta step 211.29500343057222, bounds [0,33.84424612726798]. Three disposable branches clone identical model parameters, Adam moments and branch RNG immediately before the actual update. They update on the same arrived record at the old coefficient, selected coefficient, or the reflected coefficient clipped to the same bounds. They then forecast the current scheduled origin using available predictors. Only the actual continuous branch contributes to future parent states.

The diagnostic runs the first 28 scheduled ticks, with three initial target epochs and one online epoch. Only registered calibration origins with complete next-day labels are scored after replay. Pair counts per seed are 23 for 1405 and 25 for each other target. Decisions without a subsequent issued forecast are excluded. Projection asymmetry is explicitly flagged (21 pairs). There is no matched next forecast for every meta decision.

All 294 follow-branch vectors match the actual saved continuous replay vectors exactly. Each disposable evaluation checks that the actual model/optimizer/RNG snapshot remains unchanged. Input files were authenticated before execution and rehashed after all twelve cells. Source identities are retained in summary.json. Raw publisher archives were not freshly checked. Model/RNG isolation has a fixture regression test. This is a one-step comparison on an exposed Development calibration set, with dependent days and previously selected hyperparameters.

## Reproduce

Run from the repository with Python 3.12 and the model dependencies installed.

```sh
python -m tools.issue99_decision_probe --input INPUT_ROOT --sources SOURCE_PARENT --output NEW_OUTPUT_ROOT
```

SOURCE_PARENT contains source-seed42/epoch-10.pt through source-seed44/epoch-10.pt. The output directory must be new. The tool authenticates the input manifest and checkpoint metadata and records source byte hashes. Large checkpoints and replay artifacts remain outside Git at /Users/quyenmanh/Developer/TFL-EV/runs/issue99-decision-probe-20261110-v2. registration.json is written before execution. Each cell retains its executed config and normal runner binding. summary.json records the twelve completed cells. The script hash authenticates the diagnostic implementation alongside the inherited code identity.

## Remaining questions

The full-run #102 controller result and this local diagnostic address different questions. Fixed representative regimes and practical-equivalence regions still require stability checks across calibration windows. Controller interval candidates still require matched complete replays and a declared selection criterion. The previous [0,33.844] cap was not identified as optimal by this probe. No new bound or controller recipe is promoted by these small observed differences.

Maintained evidence includes cells.csv, paired-errors.csv, summary.json and verification.json. Existing study outputs remain at their original locations.

A first run preserved at the v1 path used exact floating-point equality when flagging projection asymmetry. The v2 rerun uses a numerical tolerance; all twelve arm means match v1 exactly. This corrects a diagnostic flag only.
