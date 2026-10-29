# Hùng bounded Final WAPE audit (v1)

The private [Kaggle CPU WAPE saved version `/1`](https://www.kaggle.com/code/hungluongduc/hung-final-360-wape-20261029-v1) mounted the exact frozen GPU Final `/1` output, rechecked archive SHA-256 `531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114`, and recomputed scored-label totals and absolute errors from all 360 terminal checkpoints. Its receipt reports `FINAL_WAPE_DENOMINATORS_READ_FROM_CHECKPOINTS`, 360 jobs and zero undefined denominators. The small 64,798-byte row output has SHA-256 `5d9eafd520b3d9aedf88d6ccf0a032dce97ac30958059ebaf6067d40cb641dda` and stays in ignored `.cache`.

The CPU [audit script](../../../tools/hung_final_wape_audit_v1.py) checks the receipt hash, exact job set against the independent remote-readback ledger and score output, every scored-day count, every absolute-error sum, original-kWh MAE identity, positive label denominator and WAPE ratio. It writes [360 run rows](wape_runs.csv), [station/variant/budget rows](wape_stations.csv) and [summary](wape_summary.json). The CSV/JSON SHA-256 values are `59aa644c94e25f161e00d610246bfd2fe46fa05d5f11fa91ec6a016c61ff922b`, `74bf125b7075d6a80eefcb7abc1e443031e9e204b77ab0d99829f8dd20fa16ab` and `b188d31bb5a0d433a70d224eaa0b8bf26904822defd862b1fe5cff05c2f0ee5b` respectively.

WAPE is `sum(|forecast-label|) / sum(label)` over each job's **scored 24-hour horizons only**. The table first averages physical-seed WAPE within a station, then stations equally within each variant/budget. It does not pool energy across stations, count the deterministic Seasonal Naive's one seed three times, or turn unscored horizons into zeros.

| Budget | Main WAPE | Target-only WAPE | Source-error WAPE | Full-finetuning WAPE | Seasonal Naive WAPE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 d | 0.515553 | 0.860639 | 0.504968 | 0.507169 | 0.743792 |
| 14 d | 0.522927 | 0.843344 | 0.509947 | 0.506286 | 0.743792 |
| 28 d | 0.514267 | 0.786495 | 0.504625 | 0.504448 | 0.743792 |

Each value is descriptive over three locked SZH UrbanEV stations. Main improves over Target-only but does not have the lowest observed WAPE. The 370 other eligible UrbanEV IDs and six CHARGED city scopes are outside this Final lock; no broader population claim follows.

Reproduce from the repository root after fetching only the two small Kaggle CPU outputs into the listed create-only `.cache` paths:

```sh
python -m tools.hung_final_wape_audit_v1 \
  --scores .cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-run-scores.json \
  --wape .cache/hung-final-wape-20261029-v1/saved-output-v1-complete/final-wape-rows.json \
  --receipt .cache/hung-final-wape-20261029-v1/saved-output-v1-complete/final-wape-receipt.json \
  --ledger .cache/hung-final-direct-readback-20261029-v1/saved-output-v1-complete/final-job-artifact-ledger.json \
  --output .cache/hung-final-wape-audit-NEW
```

The output directory must not already exist. The original 2.4 GB archive and 10.6 GB provider output are unnecessary for this local audit because the saved Kaggle CPU version performed the checkpoint readback in place.
