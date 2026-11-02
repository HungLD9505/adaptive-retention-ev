# Bounded Final scored-origin symmetry audit

The [machine audit](hung-final-coverage-symmetry-20261030-v1.json), SHA-256 `6831ce58e0e679f8a91c85e4b25617db28fd72915a9cc70afc38fbf7b524e9e8`, checked the exact 360-job Final CPU score source and its receipt against the tracked [run table](hung-final-analysis-20261029-v1/runs.csv). Input identities: score source SHA-256 `9e09ae4f72b13c03ed029deb338301753ae377c15cbbfa7414433c5538cba73a` (5,998,020 bytes), receipt SHA-256 `657264b1330d48b77f65ea032e3a69f351c6ba8f657a3ae432a3e1060b23bc65`, run-table SHA-256 `2e26b3f99a11e7acc9de539dc08f07dbbb8dad9cbc6c53fb30ae71cba48d4491`. The audit checks the frozen lock and Kaggle saved version from the receipt, exact job IDs, station/budget/seed/variant identities, 90 scheduled and issued origins per job, scored-hour counts, and all scored-day sets and label hashes **within each station and budget**.

| SZH UrbanEV station | History budget | Physical jobs | Issued origins | Scored origins | Unscored origins | Common unscored day |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2118 | 7 days | 40 | 3,600 | 3,560 | 40 | 2022-12-09, +08:00 |
| 2118 | 14 days | 40 | 3,600 | 3,560 | 40 | 2022-12-09, +08:00 |
| 2118 | 28 days | 40 | 3,600 | 3,560 | 40 | 2022-12-09, +08:00 |
| 2534 | 7/14/28 days, each | 40 per budget | 3,600 per budget | 3,600 per budget | 0 | None |
| 2579 | 7/14/28 days, each | 40 per budget | 3,600 per budget | 3,600 per budget | 0 | None |

Across all 360 physical jobs, 32,400 origins were issued and 32,280 were scored. All 120 unscored job-origins are the **same single calendar day** for station 2118, repeated across the 40 locked physical jobs at each of the three budgets. Within every station/budget, all 40 methods/seeds have the same scored-day set and the same saved original-kWh label SHA for each scored day. Thus the observed missingness is method-symmetric for the locked comparison cells; it is not 120 different missing days or a zero-valued error. The audit does not establish why that source label is unavailable, real-world label-arrival timing, or equality of byte hashes across different budget scalers. Each Final job still has 89 or 90 complete scored days and non-null aggregate MAE/RMSE.

Reproduce from repository root using the existing small, ignored CPU score source:

```sh
python -m tools.hung_final_coverage_symmetry_audit_v1 \
  --scores .cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-run-scores.json \
  --receipt .cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-metrics-receipt.json \
  --runs docs/reports/hung-final-analysis-20261029-v1/runs.csv \
  --output NEW_CREATE_ONLY_PATH.json
```

The CLI refuses an existing output. Three synthetic regressions cover the shared missing day, method-specific missing dates and method-specific label changes. This analysis only checks the already authenticated score export's comparison support; it does not download the Final archive, modify the frozen run or constitute non-author scientific acceptance.
