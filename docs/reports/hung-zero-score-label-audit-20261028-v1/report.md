# Frozen Development input audit for 407 zero-scored runs

**Status (28 October 2026): bounded input-cause finding, not new scored results or Final evidence.** This audit extends the [851-run Development CPU report](../hung-development-audit-20261028-v2/report.md). It explains why the saved input snapshot cannot score the 11 affected station × budget cells, without filling any label or changing the old runs.

## Immutable bindings

- Repo-local Development input ZIP: `.cache/kaggle-payload-v2/payload/inputs.zip`, 151,254,390 bytes, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. Its 7/14/28-day `manifest.json` member SHA-256 values exactly equal the corresponding input-manifest SHA values in all 782 rows of the [v5 job ledger](../hung-development-782-job-ledger-20261028-v5.csv). The ZIP/member hashes are in [summary.json](summary.json).
- The source [407-row zero-scored table](../hung-development-audit-20261028-v2/zero_scored.csv) has SHA-256 `653f4a2ba1e3217e3a775c36849093f6be9b03d28550f333519d6c093b423ff1`. Its job IDs, input-manifest hashes and created counts were matched to the pinned 851-run merged source (SHA-256 `82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d`). Each cell contains 34 new jobs in the v5 ledger and three historical Main anchors. The historical anchors' input hashes were checked against their merged records, not by reopening external historical checkpoint bytes.
- For each selected entity, the ZIP has 90 distinct schedule origins and 90 matching label records. The selected schedules contain 550 `created` and 440 `skipped_all_missing_history` origins. The entity coverage rows agree with these counts. The [550-row per-origin table](origin_labels.csv) records the SHA-256 of each serialized label line and its exact missing-bin counts; [cells.csv](cells.csv) aggregates the 11 cells.

## Finding

**All 550 created origins have an incomplete frozen 24-hour label horizon.** Every one has at least one hourly bin with `file_valid=false` and `energy_kwh=null`. Across these origins, 3,970 hourly bins have both properties. No created origin has a complete horizon available by the replay end, and none is a complete horizon that merely arrives after that end. The input manifest declares `availability_delay_hours=0`; the per-origin audit also found zero availability timestamps after the replay end. The project `ready_labels` gate independently returns no complete 24-hour labels for these origins. Repeating the 550 origins across 37 method/seed runs per cell accounts for **20,350 unscored created forecasts** in the 407-run table.

| Budget days | Station | Created origins | Invalid/missing hourly bins | Initial target trainable examples |
| ---: | ---: | ---: | ---: | ---: |
| 7 | 1050 | 90 | 708 | 0 |
| 7 | 1200 | 59 | 332 | 0 |
| 7 | 2447 | 59 | 540 | 0 |
| 14 | 1025 | 43 | 426 | 0 |
| 14 | 1987 | 3 | 70 | 1 |
| 14 | 2613 | 59 | 327 | 0 |
| 14 | 2644 | 59 | 331 | 0 |
| 28 | 1188 | 59 | 331 | 0 |
| 28 | 1251 | 58 | 412 | 0 |
| 28 | 1408 | 58 | 423 | 0 |
| 28 | 1987 | 3 | 70 | 13 |
| **Total** | **11 cells** | **550** | **3,970** | — |

Nine cells are declared `source_checkpoint_only` because their initial target budget has zero trainable examples. The two 1987 cells have 1 or 13 initial examples and `target_initial_adaptation`; both still have no complete *replay* label day. Initialization stratum and replay scoring are separate facts. The 440 schedule skips reflect all-missing histories, not failed model jobs.

This resolves the earlier ambiguity **within the frozen Development input**: zero scoring is caused by incomplete/missing hourly labels in that snapshot, not solely by delayed arrival of otherwise complete labels. It does **not** establish why the upstream raw producer has missing/invalid hours or whether a future source-data correction could produce new valid labels. Such a correction would require a new input/run version and a separately reviewed protocol; it cannot retroactively turn old null metrics into scores. The [748 blocked paired cells](../hung-development-audit-20261028-v2/blocked_pairs.csv) remain blocked under the original input and `no_paired_scored_days` reason.

## Reproduce and checks

From the repository root, run the create-only audit into a **new** directory:

```powershell
$env:PYTHONUTF8='1'
python -m tools.hung_zero_score_label_audit --input-zip .cache/kaggle-payload-v2/payload/inputs.zip --zero-csv docs/reports/hung-development-audit-20261028-v2/zero_scored.csv --merged .cache/development-851-merged-results.json --ledger docs/reports/hung-development-782-job-ledger-20261028-v5.csv --output-dir .cache/hung-zero-score-label-audit-reproduction-NEW
python -m unittest tests.test_hung_zero_score_label_audit -v
```

The script refuses changed input hashes, mismatched 407/782/851 job IDs or counts, any extra/missing origin, and an existing output directory. It reads only Development input ZIP members and tracked/ignored Development accounting files inside this repository. The actual run succeeded and a second create-only run produced byte-identical `cells.csv`, `origin_labels.csv` and `summary.json` (SHA-256 `a1c543ea4353824be69af7268abb865ff34b9d5926e67444cabdce6f9d6da048`, `c3543edf37127e68f01ad48246d85a29caee19c6669454716ceb36f957d46c17`, `a1894b2473e8cbe31d6741303c093b462480c415ec352f024c982f4b4ed1494d`). Three classification tests, Ruff lint/format, `py_compile`, link checks and `git diff --check` passed. No training, GPU, provider call or Final/test read was used.
