# Development 851-run matrix independent arithmetic cross-check

**Scope, 29 October 2026:** read-only recomputation of run counts, null-score identities, pair membership, and station-first arithmetic from the already published Development matrix. This verifies the internal consistency of the published *analytical records*. It does not reopen all 851 original checkpoints or establish independent scientific acceptance, Block7 fairness, causal label availability, or held-out effectiveness.

| Pinned input | SHA-256 |
| --- | --- |
| Ignored repository-local `.cache/development-851-merged-results.json` | `82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d` |
| [Zero-score rows](hung-development-audit-20261028-v2/zero_scored.csv) | `653f4a2ba1e3217e3a775c36849093f6be9b03d28550f333519d6c093b423ff1` |
| [Blocked pairs](hung-development-audit-20261028-v2/blocked_pairs.csv) | `4e5602896e542cdafa8768b2554552a54eab929316890b0a79bb05509dcaf55c` |
| [Station-first table](hung-development-hybrid-20261028-v7/paired.csv) | `307f9a2115cdc8b2f386154863d75751de6ab9447b476335fa5ad7b69e79237d` |

The [separate cross-checker](../../tools/hung_development_matrix_crosscheck_v1.py) recomputed 851 unique run IDs and cohort keys, 444 scored and 407 null-scored runs. Every null-scored job ID matches the zero-score CSV exactly, and `metrics is None` agrees with zero scored days for all 851 runs. It found 816 unique valid pair keys, 748 unique blocked pair keys, no overlap, no reference to an absent run, and exact blocked-pair CSV reason/key equality. Each valid pair has positive paired days and 24 paired hours per day on both sides. All 72 station-first groups have the stated station and minimum-seed counts. Recomputing equal-seed MAE/RMSE within each station and equal-station means, absolute/relative MAE gain and worse-than-reference station fraction yielded **zero numerical mismatches** at `1e-12` absolute/relative tolerance; the published station-first CSV keys and checked MAE/gain values also match.

This confirms arithmetic and table transcription against the **same merged source**, not independent raw-forecast recomputation. In particular, the 407 null runs remain missing observations rather than zero-valued errors. The 748 blocked pairs remain excluded; the cross-check does not convert them into valid comparisons. The matrix's 69 historical Main anchors remain a different receipt class from the 782 new jobs. The [existing label-origin audit](hung-zero-score-label-audit-20261028-v1/report.md), [Development ledger](hung-development-782-job-ledger-20261028-v5.csv) and [hybrid report](hung-development-hybrid-20261028-v7/report.md) retain their narrower provenance claims.

## Reproduce

From the repository root, with the pinned ignored merged JSON present:

```powershell
python -X utf8 -m tools.hung_development_matrix_crosscheck_v1 --matrix .cache/development-851-merged-results.json --zero docs/reports/hung-development-audit-20261028-v2/zero_scored.csv --blocked docs/reports/hung-development-audit-20261028-v2/blocked_pairs.csv --station docs/reports/hung-development-hybrid-20261028-v7/paired.csv --matrix-sha256 82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d
```

The command printed `unique_runs=851`, `scored_runs=444`, `null_scored_runs=407`, `valid_pairs=816`, `blocked_pairs=748`, `station_first_groups=72`, and `station_first_numeric_mismatches=0`, then exited 0. The auditor writes no output. Five synthetic regressions check valid input, duplicate run IDs, altered station MAE, invalid paired-hour counts and a changed matrix hash; they do not substitute for the original input hashes. No training, Final lock or old report was changed.
