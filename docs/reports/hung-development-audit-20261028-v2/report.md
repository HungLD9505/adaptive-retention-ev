# Hung Development CPU audit (2026-10-28)

## Scope and pins

This report analyzes saved **Development** results only. It does not choose a Final model or use Final/test scores. The merged 851-run source is `.cache/development-851-merged-results.json` (SHA-256 `82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d`). The 782-job ledger is `docs/reports/hung-development-782-job-ledger-20261028-v5.csv` (SHA-256 `bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004`). The audit requires the exact 782 dispatch job IDs to equal the ledger set. Its CSV files are the complete row-level evidence, including explicit empty fields for unknown or inapplicable values.

## Coverage and blocked comparisons

Of 851 physical runs, 444 have scored metrics and **407 have zero scored days**. All 407 created forecasts and recorded `unscored_created = created`, with `metrics = null`. They occupy exactly 11 station × budget cells, each with 37 method/seed runs:

| Budget (days) | Station IDs | Zero-scored runs |
| --- | --- | ---: |
| 7 | 1050, 1200, 2447 | 111 |
| 14 | 1025, 1987, 2613, 2644 | 148 |
| 28 | 1188, 1251, 1408, 1987 | 148 |

The saved coverage records show forecast creation and zero scored days. They **do not establish why labels are absent**, or whether labels could later arrive. The precise created/requested/skipped counts for each run and cell are in `zero_scored.csv` and `summary.json`. There are 816 valid paired cells and **748 blocked paired cells**; every blocked row's saved reason is `no_paired_scored_days` (68 pairs per zero-scored cell). See `blocked_pairs.csv` for method, reference, seed and station.

## Paired gains, uncertainty and negative transfer

The 72 method × reference × budget groups use equal weight for seeds within a station, then equal weight for scorable stations. Gain is reference error minus method error in kWh; positive means lower method error. The audit checks recomputed MAE gains against the merged result's station-first values. The 95% intervals enumerate all `n^n` station-bootstrap samples (n = 3, 4, or 5 stations), then use 2.5% and 97.5% percentiles. These are descriptive intervals with few stations, not a population guarantee. Both MAE and RMSE gains and their exact denominators are in `paired_uncertainty.csv`.

For comparisons to `target_only`, the non-null negative-transfer (station MAE gain < 0) counts are:

| Budget | Methods with 0 negative-transfer stations | `no_source` | `seasonal_naive` |
| --- | --- | --- | --- |
| 7 days | 10 methods, each 0/3 | 3/3 | null (not supplied) |
| 14 days | 10 methods, each 0/4 | 3/4 | null (not supplied) |
| 28 days | 10 methods, each 0/5 | 3/5 | null (not supplied) |

The ten methods and each method/budget denominator, paired-cell count, MAE/RMSE gain and interval are listed individually in `paired_uncertainty.csv`. A null NTR means the merged source did not publish that statistic; it must not be read as zero. Among all 72 paired groups, 38 MAE intervals are wholly positive and 15 wholly negative. These counts are descriptive and include different references; they are not a method-selection rule.

## Decisions, switching, audit and cost

For **560 Kaggle jobs only**, `switch_audit_kaggle.csv` binds each row to its v5-ledger job ID, archive byte length and SHA-256, job receipt member and SHA-256, and replay-90 manifest SHA-256. The decision trace is from that saved manifest. A switch is an observed `selected_level != current_level` in an issued decision. There are 413 Kaggle runs with decision lists and 147 fixed-policy runs with `issued_count` evidence but no decision list; the latter have null decision and switch counts. The other 291 of 851 run manifests are outside this repository and are **not** included in this trace audit.

| Kaggle method | Runs with decisions | Decisions | Observed switches |
| --- | ---: | ---: | ---: |
| confidence | 197 | 1002 | 91 |
| fixed_retention | 67 | 402 | 0 |
| full_finetuning | 69 | 414 | 0 |
| online_best_lambda | 68 | 408 | 90 |
| uncertainty | 12 | 72 | 0 |

`frozen_source` (68), `target_only` (68), and `seasonal_naive` (11) are the 147 fixed-policy Kaggle runs without decision lists. The budget breakdown and audit inference/update counts are in `summary.json`; per-job values are in `switch_audit_kaggle.csv`. Switching counts are observations for 413 traces, **not complete 851-run coverage**.

All 851 merged runs have final-stage duration. Cost groups by method, budget and device are in `cost_by_method_device.csv`, with mean and P95 duration. Only 690 have complete candidate/audit split cost; **161 legacy runs have that split null**, including all 23 CPU seasonal-naive runs and 136 Tesla T4 plus 2 RTX 3050 Ti legacy runs. Proxy inference counts are separate from the split. Final-stage seconds exclude upstream training, upload and readback; Tesla T4, RTX 3050 Ti and CPU timing should not be compared as matched hardware.

## Reproduce

From the repository root, with Python 3.12+:

```powershell
$env:PYTHONUTF8='1'
python -m tools.hung_development_audit --input .cache/development-851-merged-results.json --sha256 82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d --ledger docs/reports/hung-development-782-job-ledger-20261028-v5.csv --ledger-sha256 bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004 --output-dir docs/reports/hung-development-audit-reproduction-NEW
python -m unittest discover -s tests -p test_hung_development_audit.py -v
```

The output directory must be new; the command refuses to overwrite an earlier report. No training or provider API is invoked.

## Limits and unresolved gates

The saved data do not explain the missing labels beyond the recorded `no_paired_scored_days` reason. The 69 historical Main run mapping, Block7 fairness, implementation parity, CHARGED interpretation and reviewer acceptance remain separate scientific gates. This audit is Development evidence, not a Final Evaluation or E2E acceptance.
