# Provisional Development results

Provisional; full coverage and independent review required

Recomputed runs: **351**; scorable: **186**; zero scored: **165**.

Exact daily label-hash intersection within station/seed; equal seed means within station, then equal station means within each budget. Disjoint expected job sets; no global ranking or Final selection.

Only already-arrived labels saved with issued Development forecasts are scored. Each checkpoint, manifest and supporting proof is SHA-checked. Historical unmatched runs are excluded. This report does not select configurations or authorize Final.

| Method | Runs | Scorable | Scored/requested days |
|---|---:|---:|---:|
| block28 | 69 | 36 | 2322/6210 |
| drift | 51 | 27 | 1629/4590 |
| fixed_retention | 20 | 11 | 683/1800 |
| frozen_source | 1 | 1 | 52/90 |
| main | 69 | 36 | 2322/6210 |
| online_best | 1 | 1 | 52/90 |
| parameter_retention | 1 | 1 | 52/90 |
| seasonal_naive | 12 | 7 | 477/1080 |
| source_error | 69 | 36 | 2322/6210 |
| target_only | 1 | 1 | 90/90 |
| uncertainty | 57 | 29 | 1884/5130 |

Each method/reference table uses its own paired day intersection. Different rows can have different cohorts and must not be interpreted as a global performance ranking. Cells with missing labels or unequal input/initialization/labels remain blocked. Full baseline/ablation, seed and budget coverage plus independent review are required.

| Budget | Method | Reference | Stations | Min seeds | MAE | RMSE | Reference MAE | MAE gain | Worse than reference | Negative transfer vs Target-only |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | block28 | main | 3 | 3 | 5.207440 | 7.544727 | 5.206837 | -0.000604 | 0.667 | n/a |
| 7 | block28 | target_only | 1 | 1 | 3.616167 | 5.892761 | 5.029901 | 1.413734 | 0.000 | 0.000 |
| 7 | main | target_only | 1 | 1 | 3.661227 | 5.911514 | 5.029901 | 1.368674 | 0.000 | 0.000 |
| 7 | seasonal_naive | main | 3 | 1 | 7.313067 | 10.226014 | 5.244938 | -2.068129 | 1.000 | n/a |
| 7 | seasonal_naive | target_only | 1 | 1 | 4.627778 | 7.102126 | 5.029901 | 0.402123 | 0.000 | n/a |
| 7 | source_error | main | 3 | 3 | 5.187037 | 7.504378 | 5.206837 | 0.019799 | 0.333 | n/a |
| 7 | source_error | target_only | 1 | 1 | 3.576274 | 5.838772 | 5.029901 | 1.453627 | 0.000 | 0.000 |
| 7 | target_only | main | 1 | 1 | 5.029901 | 6.262198 | 3.661227 | -1.368674 | 1.000 | n/a |
| 7 | uncertainty | main | 3 | 3 | 5.092915 | 7.338746 | 5.206837 | 0.113921 | 0.000 | n/a |
| 7 | uncertainty | target_only | 1 | 1 | 3.542390 | 5.700570 | 5.029901 | 1.487511 | 0.000 | 0.000 |
| 14 | block28 | main | 4 | 3 | 5.235566 | 7.169242 | 5.232235 | -0.003331 | 0.750 | n/a |
| 14 | drift | main | 4 | 3 | 5.147371 | 7.059111 | 5.232235 | 0.084864 | 0.250 | n/a |
| 14 | fixed_retention | main | 4 | 2 | 5.191579 | 7.124633 | 5.231670 | 0.040092 | 0.250 | n/a |
| 14 | frozen_source | main | 1 | 1 | 6.540867 | 9.107819 | 6.690553 | 0.149687 | 0.000 | n/a |
| 14 | online_best | main | 1 | 1 | 6.548480 | 8.831341 | 6.690553 | 0.142074 | 0.000 | n/a |
| 14 | source_error | main | 4 | 3 | 5.188813 | 7.120097 | 5.232235 | 0.043422 | 0.250 | n/a |
| 14 | uncertainty | main | 4 | 1 | 5.212997 | 7.119405 | 5.264968 | 0.051972 | 0.250 | n/a |
| 28 | block28 | main | 5 | 3 | 5.579476 | 7.597162 | 5.598521 | 0.019045 | 0.200 | n/a |
| 28 | drift | main | 5 | 3 | 5.564866 | 7.581545 | 5.598521 | 0.033656 | 0.200 | n/a |
| 28 | parameter_retention | main | 1 | 1 | 10.303079 | 13.562555 | 10.381852 | 0.078773 | 0.000 | n/a |
| 28 | seasonal_naive | main | 4 | 1 | 6.606611 | 8.948342 | 4.432446 | -2.174165 | 1.000 | n/a |
| 28 | source_error | main | 5 | 3 | 5.565872 | 7.580693 | 5.598521 | 0.032650 | 0.000 | n/a |
| 28 | uncertainty | main | 5 | 3 | 5.578790 | 7.590110 | 5.598521 | 0.019731 | 0.200 | n/a |

Blocked pair reasons: `{"no_paired_scored_days": 132}`.

Full result SHA: `76b9de2548dc798a37f6cbd4df7e4dbcf8ca5396e69ebe8fc3c8d3d9106cbb93`.
Catalog SHA: `b99d6ce3f46eb4fbeb3fcbae61bae589664e6a30f894b234c488c6965313b0f0`.

Runtime fields in the full JSON identify the device, final-stage duration and cumulative runner/proxy costs. Final-stage duration excludes earlier continuation/init stages; these values must not be presented as whole-job provider time. No independent acceptance, #39 completion or Final-lock claim is made.
