# Provisional Development results

Provisional; full coverage and independent review required

Recomputed runs: **191**; scorable: **101**; zero scored: **90**.

Complete hourly errors within paired station/seed; mean seeds within station, then equal station mean within each budget. Budgets remain separate. Transfer gain and negative transfer apply only to Source-using methods versus Target-only. Other comparisons report generic MAE differences/worse-than-reference fractions. Zero reference MAE gives undefined relative gain; absolute differences remain available.

Only already-arrived labels saved with issued Development forecasts are scored. Each checkpoint, manifest and supporting proof is SHA-checked. Historical unmatched runs are excluded. This report does not select configurations or authorize Final.

| Method | Runs | Scorable | Scored/requested days |
|---|---:|---:|---:|
| frozen_source | 1 | 1 | 52/90 |
| main | 69 | 36 | 2322/6210 |
| online_best | 1 | 1 | 52/90 |
| parameter_retention | 1 | 1 | 52/90 |
| seasonal_naive | 12 | 7 | 477/1080 |
| source_error | 49 | 25 | 1525/4410 |
| target_only | 1 | 1 | 90/90 |
| uncertainty | 57 | 29 | 1884/5130 |

Each method/reference table uses its own paired day intersection. Different rows can have different cohorts and must not be interpreted as a global performance ranking. Cells with missing labels or unequal input/initialization/labels remain blocked. Full baseline/ablation, seed and budget coverage plus independent review are required.

| Budget | Method | Reference | Stations | Min seeds | MAE | RMSE | Reference MAE | MAE gain | Worse than reference | Negative transfer vs Target-only |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | main | target_only | 1 | 1 | 3.661227 | 5.911514 | 5.029901 | 1.368674 | 0.000 | 0.000 |
| 7 | seasonal_naive | main | 3 | 1 | 7.313067 | 10.226014 | 5.244938 | -2.068129 | 1.000 | n/a |
| 7 | seasonal_naive | target_only | 1 | 1 | 4.627778 | 7.102126 | 5.029901 | 0.402123 | 0.000 | n/a |
| 7 | target_only | main | 1 | 1 | 5.029901 | 6.262198 | 3.661227 | -1.368674 | 1.000 | n/a |
| 7 | uncertainty | main | 3 | 3 | 5.092915 | 7.338746 | 5.206837 | 0.113921 | 0.000 | n/a |
| 7 | uncertainty | target_only | 1 | 1 | 3.542390 | 5.700570 | 5.029901 | 1.487511 | 0.000 | 0.000 |
| 14 | frozen_source | main | 1 | 1 | 6.540867 | 9.107819 | 6.690553 | 0.149687 | 0.000 | n/a |
| 14 | online_best | main | 1 | 1 | 6.548480 | 8.831341 | 6.690553 | 0.142074 | 0.000 | n/a |
| 14 | source_error | main | 4 | 3 | 5.188813 | 7.120097 | 5.232235 | 0.043422 | 0.250 | n/a |
| 14 | uncertainty | main | 4 | 1 | 5.212997 | 7.119405 | 5.264968 | 0.051972 | 0.250 | n/a |
| 28 | parameter_retention | main | 1 | 1 | 10.303079 | 13.562555 | 10.381852 | 0.078773 | 0.000 | n/a |
| 28 | seasonal_naive | main | 4 | 1 | 6.606611 | 8.948342 | 4.432446 | -2.174165 | 1.000 | n/a |
| 28 | source_error | main | 5 | 2 | 5.563248 | 7.577833 | 5.593043 | 0.029795 | 0.000 | n/a |
| 28 | uncertainty | main | 5 | 3 | 5.578790 | 7.590110 | 5.598521 | 0.019731 | 0.200 | n/a |

Blocked pair reasons: `{"no_paired_scored_days": 57}`.

Full result SHA: `f622f48b44a4238f95459b3bac3fefa58096a3ddf983cc72706aeb65f3643c19`.
Catalog SHA: `c6778ab3364555873120062672fc1b2b018a7926955cd90a4b5931ac15c383b7`.

Runtime fields in the full JSON identify the device, final-stage duration and cumulative runner/proxy costs. Final-stage duration excludes earlier continuation/init stages; these values must not be presented as whole-job provider time. No independent acceptance, #39 completion or Final-lock claim is made.
