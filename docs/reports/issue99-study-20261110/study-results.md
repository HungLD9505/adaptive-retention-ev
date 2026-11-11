# Issue #99 completed exploratory Development study

This study compares calibrated fixed latent retention with a continuous one-step validation controller. On the registered later objective, Continuous MAE is 4.806223 kWh and Fixed MAE is 4.803054 kWh. Source10, four selected UrbanEV/SZH targets, three paired seeds and 14-day initial history were reused. This is exploratory Development evidence, not fresh held-out or scientifically peer-approved evidence. The task remains 24→24. Historical reports and Final results are unchanged.

## Registered scope and selection

The first 28 scheduled origins supplied calibration, the next two were excluded from both score objectives, and the final 60 supplied the later objective. Online replay covered all 90 scheduled days with actual delayed label availability. Prior exposure to this cohort makes every result exploratory. Expected later score counts are 60/22/22/22, not 60 complete days for every station; all missing/skipped outcomes remain.

Fixed selection: lambda=0.798445006708, calibration MAE=5.331705633 kWh versus lambda0=5.443630218. Boundary unresolved: False. The selected value is best among evaluated points, not a proven global optimum. The full fixed ledger, failed/null trials and sampled regimes are exported separately; sensitivity lines connect measurements and do not estimate exact transition boundaries.

Controller interval: [0,33.8442461273], initialized at 0.798445006708. Selected eta=211.295003431, cadence=1 complete arrivals, A=2 older arrived days and V=1 newer untrained day. Selection used only registered calibration MAE among six declared recipes. The numerical bounds and scale fractions are study choices; cited hypergradient papers do not prescribe EV-specific values.

## Matched results

| Method | Later-objective MAE, kWh | Delta vs lambda0 | Full-90 descriptive MAE |
| --- | ---: | ---: | ---: |
| lambda0 | 4.868597 | +0.000000 | 5.144953 |
| fixed | 4.803054 | -0.065543 | 5.053859 |
| discrete | 4.798259 | -0.070339 | 5.098825 |
| continuous | 4.806223 | -0.062374 | 5.052390 |
| frozen_lambda | 4.803054 | -0.065543 | 5.053859 |

Continuous minus calibrated Fixed on the later objective is **+0.003169 kWh**; a negative value favors Continuous. This is the main mechanism comparison, not the earlier calibration improvement.

| Target | lambda0 | Fixed | Discrete | Continuous | Frozen |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1405 | 5.386140 | 5.235166 | 5.283969 | 5.203826 | 5.235166 |
| 2152 | 6.124389 | 5.981652 | 6.030500 | 6.090296 | 5.981652 |
| 1153 | 6.532764 | 6.426777 | 6.393199 | 6.393993 | 6.426777 |
| 1693 | 1.431097 | 1.568621 | 1.485368 | 1.536778 | 1.568621 |

All entries average paired seeds within station, then give the four stations equal weight. The full-90 column mixes calibration and later days and is descriptive only. Frozen lambda may exactly reuse Fixed when all executable configurations match; it is not an independently retrained replicate. The legacy discrete controller keeps its original recipe and three shadow models, with greater compute and different initialization than the single-branch methods. It was not retuned for this new calibration split, so tuning budgets differ and its gap cannot be attributed solely to the controller mechanism.

## Interpretation and limits

Read the paired station results and seed ranges with the aggregate. Four historically selected stations in one city are a small dependent cohort. No significance, universal transfer/GRU superiority, or calibrated safe-adaptation guarantee is established. Coefficient movement and gradient ratios are diagnostics, not proof of forecast improvement. Negative comparisons remain visible. This study does not replace the separate backbone/transfer baseline work in issue #97.

The implemented loss/update formulas and paper attribution remain in the preceding verification handoff. Fixed uses a constant real coefficient; continuous uses a projected one-step current-Adam validation hypergradient with a frozen Source encoder/reference scale. No custom GRU cell or silent loss redesign was introduced.

## Verification and artifacts

The independent matrix verifier recomputed saved-prediction errors from authenticated complete arrived labels, required exact method/seed/target identities, matched scored origins and checked each retained tick commitment. It permits explicitly pruned historical states under latest-only retention, while checking the newest full checkpoint. Input bytes were rehashed after execution and report extraction. Runtime/source/code/config hashes are in the run bindings. Publisher raw archives were not freshly checked.

See CSV/JSON records for full precision, costs, coverage, regimes, per-day errors and trajectories; PNG/PDF figures are standalone export artifacts. Historical Source pretraining/billing totals are unknown and must not be reconstructed from update counts. Owner execution authorization does not waive the repository's merge policy.
