# Provisional Development results

Provisional; full coverage and independent review required

Recomputed runs: **851**; scorable: **444**; zero scored: **407**.

Exact daily label-hash intersection within station/seed; equal seed means within station, then equal station means within each budget. Disjoint expected job sets; no global ranking or Final selection.

Only already-arrived labels saved with issued Development forecasts are scored. Each checkpoint, manifest and supporting proof is SHA-checked. Historical unmatched runs are excluded. This report does not select configurations or authorize Final.

| Method | Runs | Scorable | Scored/requested days |
|---|---:|---:|---:|
| block28 | 69 | 36 | 2322/6210 |
| drift | 69 | 36 | 2322/6210 |
| fixed_retention | 69 | 36 | 2322/6210 |
| frozen_source | 69 | 36 | 2322/6210 |
| full_finetuning | 69 | 36 | 2322/6210 |
| main | 69 | 36 | 2322/6210 |
| no_source | 69 | 36 | 2322/6210 |
| online_best | 69 | 36 | 2322/6210 |
| parameter_retention | 69 | 36 | 2322/6210 |
| seasonal_naive | 23 | 12 | 774/2070 |
| source_error | 69 | 36 | 2322/6210 |
| target_only | 69 | 36 | 2322/6210 |
| uncertainty | 69 | 36 | 2322/6210 |

Each method/reference table uses its own paired day intersection. Different rows can have different cohorts and must not be interpreted as a global performance ranking. Cells with missing labels or unequal input/initialization/labels remain blocked. Full baseline/ablation, seed and budget coverage plus independent review are required.

| Budget | Method | Reference | Stations | Min seeds | MAE | RMSE | Reference MAE | MAE gain | Worse than reference | Negative transfer vs Target-only |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | block28 | main | 3 | 3 | 5.207440 | 7.544727 | 5.206837 | -0.000604 | 0.667 | n/a |
| 7 | block28 | target_only | 3 | 3 | 5.207440 | 7.544727 | 8.656700 | 3.449260 | 0.000 | 0.000 |
| 7 | drift | main | 3 | 3 | 5.139197 | 7.438881 | 5.206837 | 0.067639 | 0.333 | n/a |
| 7 | drift | target_only | 3 | 3 | 5.139197 | 7.438881 | 8.656700 | 3.517503 | 0.000 | 0.000 |
| 7 | fixed_retention | main | 3 | 3 | 5.201225 | 7.526943 | 5.206837 | 0.005612 | 0.333 | n/a |
| 7 | fixed_retention | target_only | 3 | 3 | 5.201225 | 7.526943 | 8.656700 | 3.455476 | 0.000 | 0.000 |
| 7 | frozen_source | main | 3 | 3 | 5.283687 | 7.901793 | 5.206837 | -0.076850 | 1.000 | n/a |
| 7 | frozen_source | target_only | 3 | 3 | 5.283687 | 7.901793 | 8.656700 | 3.373014 | 0.000 | 0.000 |
| 7 | full_finetuning | main | 3 | 3 | 5.093954 | 7.338788 | 5.206837 | 0.112883 | 0.333 | n/a |
| 7 | full_finetuning | target_only | 3 | 3 | 5.093954 | 7.338788 | 8.656700 | 3.562747 | 0.000 | 0.000 |
| 7 | main | target_only | 3 | 3 | 5.206837 | 7.536425 | 8.656700 | 3.449864 | 0.000 | 0.000 |
| 7 | no_source | main | 3 | 3 | 9.103865 | 11.160824 | 5.206837 | -3.897028 | 1.000 | n/a |
| 7 | no_source | target_only | 3 | 3 | 9.103865 | 11.160824 | 8.656700 | -0.447164 | 1.000 | 1.000 |
| 7 | online_best | main | 3 | 3 | 5.204189 | 7.509287 | 5.206837 | 0.002648 | 0.333 | n/a |
| 7 | online_best | target_only | 3 | 3 | 5.204189 | 7.509287 | 8.656700 | 3.452512 | 0.000 | 0.000 |
| 7 | parameter_retention | main | 3 | 3 | 5.093151 | 7.340244 | 5.206837 | 0.113686 | 0.333 | n/a |
| 7 | parameter_retention | target_only | 3 | 3 | 5.093151 | 7.340244 | 8.656700 | 3.563549 | 0.000 | 0.000 |
| 7 | seasonal_naive | main | 3 | 1 | 7.313067 | 10.226014 | 5.244938 | -2.068129 | 1.000 | n/a |
| 7 | seasonal_naive | target_only | 3 | 1 | 7.313067 | 10.226014 | 8.711652 | 1.398585 | 0.000 | n/a |
| 7 | source_error | main | 3 | 3 | 5.187037 | 7.504378 | 5.206837 | 0.019799 | 0.333 | n/a |
| 7 | source_error | target_only | 3 | 3 | 5.187037 | 7.504378 | 8.656700 | 3.469663 | 0.000 | 0.000 |
| 7 | target_only | main | 3 | 3 | 8.656700 | 10.823208 | 5.206837 | -3.449864 | 1.000 | n/a |
| 7 | uncertainty | main | 3 | 3 | 5.092915 | 7.338746 | 5.206837 | 0.113921 | 0.000 | n/a |
| 7 | uncertainty | target_only | 3 | 3 | 5.092915 | 7.338746 | 8.656700 | 3.563785 | 0.000 | 0.000 |
| 14 | block28 | main | 4 | 3 | 5.235566 | 7.169242 | 5.232235 | -0.003331 | 0.750 | n/a |
| 14 | block28 | target_only | 4 | 3 | 5.235566 | 7.169242 | 7.666792 | 2.431226 | 0.000 | 0.000 |
| 14 | drift | main | 4 | 3 | 5.147371 | 7.059111 | 5.232235 | 0.084864 | 0.250 | n/a |
| 14 | drift | target_only | 4 | 3 | 5.147371 | 7.059111 | 7.666792 | 2.519421 | 0.000 | 0.000 |
| 14 | fixed_retention | main | 4 | 3 | 5.190855 | 7.120801 | 5.232235 | 0.041380 | 0.250 | n/a |
| 14 | fixed_retention | target_only | 4 | 3 | 5.190855 | 7.120801 | 7.666792 | 2.475937 | 0.000 | 0.000 |
| 14 | frozen_source | main | 4 | 3 | 5.491232 | 7.618020 | 5.232235 | -0.258997 | 0.750 | n/a |
| 14 | frozen_source | target_only | 4 | 3 | 5.491232 | 7.618020 | 7.666792 | 2.175560 | 0.000 | 0.000 |
| 14 | full_finetuning | main | 4 | 3 | 5.191221 | 7.093668 | 5.232235 | 0.041013 | 0.750 | n/a |
| 14 | full_finetuning | target_only | 4 | 3 | 5.191221 | 7.093668 | 7.666792 | 2.475571 | 0.000 | 0.000 |
| 14 | main | target_only | 4 | 3 | 5.232235 | 7.164760 | 7.666792 | 2.434557 | 0.000 | 0.000 |
| 14 | no_source | main | 4 | 3 | 8.062977 | 9.981400 | 5.232235 | -2.830742 | 1.000 | n/a |
| 14 | no_source | target_only | 4 | 3 | 8.062977 | 9.981400 | 7.666792 | -0.396185 | 0.750 | 0.750 |
| 14 | online_best | main | 4 | 3 | 5.175367 | 7.091490 | 5.232235 | 0.056868 | 0.000 | n/a |
| 14 | online_best | target_only | 4 | 3 | 5.175367 | 7.091490 | 7.666792 | 2.491425 | 0.000 | 0.000 |
| 14 | parameter_retention | main | 4 | 3 | 5.187052 | 7.089247 | 5.232235 | 0.045183 | 0.500 | n/a |
| 14 | parameter_retention | target_only | 4 | 3 | 5.187052 | 7.089247 | 7.666792 | 2.479740 | 0.000 | 0.000 |
| 14 | seasonal_naive | main | 4 | 1 | 7.073098 | 9.567370 | 5.298076 | -1.775022 | 1.000 | n/a |
| 14 | seasonal_naive | target_only | 4 | 1 | 7.073098 | 9.567370 | 7.669108 | 0.596010 | 0.250 | n/a |
| 14 | source_error | main | 4 | 3 | 5.188813 | 7.120097 | 5.232235 | 0.043422 | 0.250 | n/a |
| 14 | source_error | target_only | 4 | 3 | 5.188813 | 7.120097 | 7.666792 | 2.477979 | 0.000 | 0.000 |
| 14 | target_only | main | 4 | 3 | 7.666792 | 9.658510 | 5.232235 | -2.434557 | 1.000 | n/a |
| 14 | uncertainty | main | 4 | 3 | 5.168888 | 7.072091 | 5.232235 | 0.063347 | 0.500 | n/a |
| 14 | uncertainty | target_only | 4 | 3 | 5.168888 | 7.072091 | 7.666792 | 2.497904 | 0.000 | 0.000 |
| 28 | block28 | main | 5 | 3 | 5.579476 | 7.597162 | 5.598521 | 0.019045 | 0.200 | n/a |
| 28 | block28 | target_only | 5 | 3 | 5.579476 | 7.597162 | 8.099551 | 2.520075 | 0.000 | 0.000 |
| 28 | drift | main | 5 | 3 | 5.564866 | 7.581545 | 5.598521 | 0.033656 | 0.200 | n/a |
| 28 | drift | target_only | 5 | 3 | 5.564866 | 7.581545 | 8.099551 | 2.534686 | 0.000 | 0.000 |
| 28 | fixed_retention | main | 5 | 3 | 5.558037 | 7.555955 | 5.598521 | 0.040484 | 0.000 | n/a |
| 28 | fixed_retention | target_only | 5 | 3 | 5.558037 | 7.555955 | 8.099551 | 2.541514 | 0.000 | 0.000 |
| 28 | frozen_source | main | 5 | 3 | 5.979928 | 8.200498 | 5.598521 | -0.381406 | 0.800 | n/a |
| 28 | frozen_source | target_only | 5 | 3 | 5.979928 | 8.200498 | 8.099551 | 2.119623 | 0.000 | 0.000 |
| 28 | full_finetuning | main | 5 | 3 | 5.582078 | 7.620297 | 5.598521 | 0.016443 | 0.400 | n/a |
| 28 | full_finetuning | target_only | 5 | 3 | 5.582078 | 7.620297 | 8.099551 | 2.517473 | 0.000 | 0.000 |
| 28 | main | target_only | 5 | 3 | 5.598521 | 7.610117 | 8.099551 | 2.501030 | 0.000 | 0.000 |
| 28 | no_source | main | 5 | 3 | 8.211336 | 10.231223 | 5.598521 | -2.612815 | 1.000 | n/a |
| 28 | no_source | target_only | 5 | 3 | 8.211336 | 10.231223 | 8.099551 | -0.111785 | 0.600 | 0.600 |
| 28 | online_best | main | 5 | 3 | 5.566769 | 7.595168 | 5.598521 | 0.031752 | 0.200 | n/a |
| 28 | online_best | target_only | 5 | 3 | 5.566769 | 7.595168 | 8.099551 | 2.532782 | 0.000 | 0.000 |
| 28 | parameter_retention | main | 5 | 3 | 5.576611 | 7.614586 | 5.598521 | 0.021910 | 0.400 | n/a |
| 28 | parameter_retention | target_only | 5 | 3 | 5.576611 | 7.614586 | 8.099551 | 2.522940 | 0.000 | 0.000 |
| 28 | seasonal_naive | main | 5 | 1 | 8.374712 | 10.996897 | 5.622327 | -2.752385 | 1.000 | n/a |
| 28 | seasonal_naive | target_only | 5 | 1 | 8.374712 | 10.996897 | 8.052825 | -0.321887 | 0.600 | n/a |
| 28 | source_error | main | 5 | 3 | 5.565872 | 7.580693 | 5.598521 | 0.032650 | 0.000 | n/a |
| 28 | source_error | target_only | 5 | 3 | 5.565872 | 7.580693 | 8.099551 | 2.533680 | 0.000 | 0.000 |
| 28 | target_only | main | 5 | 3 | 8.099551 | 10.166356 | 5.598521 | -2.501030 | 1.000 | n/a |
| 28 | uncertainty | main | 5 | 3 | 5.578790 | 7.590110 | 5.598521 | 0.019731 | 0.200 | n/a |
| 28 | uncertainty | target_only | 5 | 3 | 5.578790 | 7.590110 | 8.099551 | 2.520761 | 0.000 | 0.000 |

Blocked pair reasons: `{"no_paired_scored_days": 748}`.

Full result SHA: `82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d`.
Catalog SHA: `7a1d854dfedcad9fb4a4fe8307e5ae340027d2f00352b0924b12ba45e21812fe`.

Runtime fields in the full JSON identify the device, final-stage duration and cumulative runner/proxy costs. Final-stage duration excludes earlier continuation/init stages; these values must not be presented as whole-job provider time. No independent acceptance, #39 completion or Final-lock claim is made.
