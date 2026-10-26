# Provisional Development results

Provisional; full coverage and independent review required

Recomputed runs: **111**; scorable: **60**; zero scored: **51**.

Complete hourly errors within paired station/seed; mean seeds within station, then equal station mean within each budget. Budgets remain separate. Negative transfer is station mean MAE above its paired reference; zero reference MAE gives undefined relative gain.

Only already-arrived labels saved with issued Development forecasts are scored. Each checkpoint, manifest and supporting proof is SHA-checked. Historical unmatched runs are excluded. This report does not select configurations or authorize Final.

| Method | Runs | Scorable | Scored/requested days |
|---|---:|---:|---:|
| frozen_source | 1 | 1 | 52/90 |
| main | 69 | 36 | 2322/6210 |
| online_best | 1 | 1 | 52/90 |
| parameter_retention | 1 | 1 | 52/90 |
| seasonal_naive | 1 | 1 | 90/90 |
| target_only | 1 | 1 | 90/90 |
| uncertainty | 37 | 19 | 1288/3330 |

Each method/reference table uses its own paired day intersection. Different rows can have different cohorts and must not be interpreted as a global performance ranking. Cells with missing labels or unequal input/initialization/labels remain blocked. Full baseline/ablation, seed and budget coverage plus independent review are required.

| Budget | Method | Reference | Stations | Min seeds | MAE | RMSE | Reference MAE | MAE gain | Negative transfer stations |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 7 | main | target_only | 1 | 1 | 3.661227 | 5.911514 | 5.029901 | 1.368674 | 0.000 |
| 7 | seasonal_naive | main | 1 | 1 | 4.627778 | 7.102126 | 3.661227 | -0.966550 | 1.000 |
| 7 | seasonal_naive | target_only | 1 | 1 | 4.627778 | 7.102126 | 5.029901 | 0.402123 | 0.000 |
| 7 | target_only | main | 1 | 1 | 5.029901 | 6.262198 | 3.661227 | -1.368674 | 1.000 |
| 7 | uncertainty | main | 3 | 3 | 5.092915 | 7.338746 | 5.206837 | 0.113921 | 0.000 |
| 7 | uncertainty | target_only | 1 | 1 | 3.542390 | 5.700570 | 5.029901 | 1.487511 | 0.000 |
| 14 | frozen_source | main | 1 | 1 | 6.540867 | 9.107819 | 6.690553 | 0.149687 | 0.000 |
| 14 | online_best | main | 1 | 1 | 6.548480 | 8.831341 | 6.690553 | 0.142074 | 0.000 |
| 14 | uncertainty | main | 4 | 1 | 5.212997 | 7.119405 | 5.264968 | 0.051972 | 0.250 |
| 28 | parameter_retention | main | 1 | 1 | 10.303079 | 13.562555 | 10.381852 | 0.078773 | 0.000 |
| 28 | uncertainty | main | 4 | 1 | 6.489743 | 8.632900 | 6.494286 | 0.004542 | 0.250 |

Blocked pair reasons: `{"no_paired_scored_days": 18}`.

Full result SHA: `56e9370abafbc1e155c7f2f9e06ad5848025c157f5018a0afe88d58b7bd4010d`.
Catalog SHA: `2d4b3aa5284552a0b82955ab5e05cdc2832f96a06a24145a1d0a7f3c2dd67da8`.

Runtime fields in the full JSON identify the device, final-stage duration and cumulative runner/proxy costs. Final-stage duration excludes earlier continuation/init stages; these values must not be presented as whole-job provider time. No independent acceptance, #39 completion or Final-lock claim is made.
