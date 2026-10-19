# CHARGED hourly adapter — Issue #17 Step 5 handoff

## Scope and accepted decision

The user accepted UrbanEV primary plus all six standard CHARGED cities as supplementary, with SZH analyzed separately. This decision is recorded in [Research Flow](../MASTER_RESEARCH_FLOW.md) and the [CHARGED hourly/QC contract](../data/CHARGED_HOURLY_CONTRACT.md). It is an acceptance of bounded research scope, not proof of original observations, independent SZH locations, clean data or strict-online causality. Implementation and #18 inputs still require peer review. No PR has been merged by the agent.

This Step 5 branch starts from dev. PRs #25–#28 remain separate review items; no unmerged processing code is imported. It preserves the common nine-column hourly layout while explicitly declaring a CHARGED local-naive clock profile; an offset-only UrbanEV consumer cannot silently treat it as the same clock. No split, scaler, cohort, tensor windows, model or pooled pretraining is implemented.

## What the adapter does

- Reads the verified original standard Hourly.zip directly; retains all metadata sites across all six cities.
- Maps released hourly volume into energy_kwh unchanged: no new aggregation, imputation or power multiplication. Source zeros remain zero.
- Emits file-valid masks/counts for finite nonnegative energy; missing/invalid labels stay empty. Each released hour expects one sample, not twelve.
- Records duration/value inconsistencies as diagnostics without filtering otherwise valid energy.
- Applies and records only the recognized metadata-header override/ID aliases in memory, validated against city code, actual counts and positive radius; raw files are untouched.
- Writes new per-city hourly.csv/qc.json plus a manifest with source/config/code/runtime/output identities. A structural failure marks the run failed; partial outputs must not be consumed.

## Real-data run

- Run ID: `issue17-hourly-v1-20261017`; UTC start `2026-10-17T16:43:36.064011+00:00`.
- Executed commit: `5f1c0a616b37ceb05d9160644950f3ae052a1add`; script SHA-256 `8ef558141a243d583ff074da854671e0b63c956220621633feab7b8d0e25d9ca`; tracked worktree was clean.
- Python 3.12.14; runtime **31.31 s**.
- Input archive: 268,720,500 bytes; size/SHA-256 and publisher MD5 freshly verified. Exact identities are in the [evidence snapshot](charged-hourly-evidence.json).
- Window: nominal local 2023-04-01 00:00 inclusive to 2023-10-01 00:00 exclusive. Start-of-hour labeling is an explicit provisional assumption; no timezone/DST conversion is claimed.
- Local output: `data/processed/charged/issue17-hourly-v1-20261017/` (ignored by Git). All CSVs are machine handoff tables; use the small manifest/QC/report for review.

| City | Sites retained | Hourly rows | Invalid energy rows | Zero-energy rows | Info header override |
| --- | ---: | ---: | ---: | ---: | --- |
| AMS | 2,449 | 10,756,008 | 0 | 6,060,614 | Not needed |
| JHB | 47 | 206,424 | 0 | 74,417 | Not needed |
| LOA | 229 | 1,005,768 | 0 | 219,676 | Explicit mapping |
| MEL | 63 | 276,696 | 0 | 82,397 | Explicit mapping |
| SPO | 47 | 206,424 | 0 | 58,384 | Explicit mapping |
| SZH | 1,445 | 6,346,440 | 0 | 440,585 | Explicit mapping |

Total: **4,280 sites**, **18,797,760 rows**, all 4,392 requested hours per site. No energy rows failed these released-file checks; this does not identify which upstream values were observed or filled. No all-zero sites were dropped.

### Duration diagnostics — not exclusion rules

| City | Volume > 0 / duration = 0 | Volume = 0 / duration > 0 | Invalid duration | All-zero volume sites retained |
| --- | ---: | ---: | ---: | ---: |
| AMS | 205 | 27 | 0 | 1,061 |
| JHB | 3 | 1,436 | 0 | 12 |
| LOA | 0 | 6 | 0 | 5 |
| MEL | 1 | 1 | 0 | 1 |
| SPO | 0 | 0 | 0 | 6 |
| SZH | 9 | 8,784 | 0 | 68 |

These are now paired hourly diagnostics for all six cities; the Step 2 empirical analysis previously covered AMS only. No cause has been assigned to these mismatches. Full-window all-zero counts remain descriptive and must not choose training/evaluation entities.

### Actual output sample

First three AMS rows, preserving the source energy tokens. Timestamp remains a nominal local label without UTC offset.

| dataset_id | city_id | entity_id | timestamp | energy_kwh | file_valid_mask | valid_sample_count | expected_sample_count | qc_flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| charged | AMS | 0 | 2023-04-01T00:00:00 | 0.0 | 1 | 1 | 1 |  |
| charged | AMS | 1 | 2023-04-01T00:00:00 | 0.0 | 1 | 1 | 1 |  |
| charged | AMS | 10 | 2023-04-01T00:00:00 | 3.083333333333333 | 1 | 1 | 1 |  |

## Verification

- **15 offline tests passed** (9 existing dev source tests + 6 adapter fixtures). They cover zero preservation/all-zero site retention, missing-hour expansion, invalid labels, duration-only diagnostics, leading-zero IDs and column-order joins, known/unknown headers, duplicate/out-of-order clocks, explicit end-label shift, failed manifests, no overwrite and raw preservation.
- Ruff lint/format, tools.sources list, pip check and git diff --check passed. CI runs offline on Ubuntu and Windows; the earlier audit PR test suites are separate until merged.
- The full 18,797,760-row real run completed. Per-city row/zero/all-zero counts agree with the prior inventory for this exact window. Thirty source ZIP members are recorded, and all output CSV hashes/sizes are in the manifest.
- Independent boundary checks compared the first/last three output rows in each city (36 rows total) with original ZIP volume tokens, IDs, timestamp labels and sample counts; all matched. This is sample verification, not a second exhaustive cell-by-cell comparison.
- No training or research-effectiveness evaluation was run. Raw archives and earlier runs were not modified.

## Handoff / remaining gates

1. Peer review the implementation, numeric/error policy and recorded clock/header assumptions; user acceptance of research scope does not replace technical review.
2. #18 consumes each dataset/city separately and reads the contract profile. Its loader must support the declared local-naive CHARGED clock deliberately; it must not attach UTC or mix clocks/cities to manufacture absolute-time alignment.
3. #18 owns permitted-prefix source/development/final splits, scaling, input masks, no-filled-Y windows, official sample counts and label-order safeguards. Keep Report 1 and existing reference dates/budgets unchanged unless separately reviewed.
4. Maintain separate five-city geographic and SZH later-period analysis; no independent unseen-location SZH headline. No shared UrbanEV/CHARGED pretraining is authorized.
5. Original/imputed status, exact DST/bin/arrival provenance, physical identity mapping and the cause of static/hourly discrepancies remain unresolved. These limit claims, even when file_valid_mask=1.
6. Issue #17 remains open until review/merge and its handoff criteria are accepted; no autonomous merge or completion claim. A passing adapter is not the completion of #18 model inputs.
