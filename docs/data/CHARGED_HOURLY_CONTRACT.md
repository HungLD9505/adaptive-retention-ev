# CHARGED hourly adapter and QC contract

Profile: **`charged-hourly-v1-local-naive`**. Issue #17 Step 5; input consumers in #18 must review the profile and implementation before using outputs.

## Accepted research scope — October 17, 2026

The user/team lead accepted **UrbanEV primary + all six standard CHARGED cities supplementary** with publisher-processing limitations. AMS/JHB/LOA/MEL/SPO provide additional geographic coverage; SZH is analyzed separately as a later-period Shenzhen release with extensive coordinate overlap with UrbanEV. Do not aggregate SZH into a headline independent external-validation score. Do not pool UrbanEV/CHARGED for pretraining or silently remove any city/site.

This accepts the bounded research scope, **not** a certificate of clean/original observations, independent physical entities, strict-online causality or readiness of model inputs. Each city's source/development/final reference split remains separate, subject to #18 review. Raw bytes are immutable. All-zero site counts over the entire 183 days are diagnostics, never an exclusion rule.

## Output layout

```text
NEW_RUN_ID/
├── manifest.json
├── AMS/ (also JHB, LOA, MEL, SPO, SZH)
│   ├── hourly.csv
│   └── qc.json
└── ...
```

Each CSV is a long table, one row for every metadata site and requested nominal hourly bin. Rows are time-major, preserving source volume-column order within a timestamp. Identity is `(dataset_id, city_id, entity_id, timestamp)`. Preserve site IDs as strings, including leading zeros. Model consumers must use IDs rather than CSV column/row positions.

| Field | Type / meaning |
| --- | --- |
| dataset_id | String `charged` |
| city_id | One of AMS/JHB/LOA/MEL/SPO/SZH |
| entity_id | Publisher's city-local clustered site ID; not a physical-station certification |
| timestamp | ISO-8601 **without offset**, nominal local hourly bin start under an explicit run assumption |
| energy_kwh | Original released hourly-volume token if finite/nonnegative; empty if invalid/missing |
| file_valid_mask | Integer 1 for a structurally unique released hourly energy entry meeting numeric checks; otherwise 0 |
| valid_sample_count | 1 for valid released hourly energy, otherwise 0; does not count original observations |
| expected_sample_count | **1**, because CHARGED already supplies hourly energy; never invent 12 five-minute observations |
| qc_flags | Empty for valid energy; `invalid_target_value` or `missing_hour` for an invalid row |

### Compatibility with the UrbanEV proposal

The nine column names/order match the common hourly layout proposed in [PR #25](https://github.com/HungLD9505/adaptive-retention-ev/pull/25). CHARGED uses one released hourly entry instead of twelve original five-minute bins, and retains offset-free publisher-local clocks. PR #25's UrbanEV profile emits offset-aware timestamps under an explicit zone assumption; **these clock profiles are not interchangeable**.

The consumer must read `manifest.contract_profile` and its clock policy, process each dataset/city independently, and preserve that information in #18 artifacts. An offset-only validator from the UrbanEV proposal must not be applied unchanged or bypassed silently. This document is the CHARGED-specific profile for consumer review; it does not rewrite the unmerged UrbanEV contract or assert drop-in compatibility with an existing loader. No model loader exists in this implementation.

## Energy validity and diagnostic rules

- Read `volume.csv` as released **hourly kWh**. No resampling, summation, power multiplication, estimation or interpolation is performed. Preserve original numeric tokens for valid energy, including zero.
- Blank/nonnumeric/NaN/infinity/negative volume yields empty energy, mask/count 0. It is never filled from neighboring hours, duration or metadata.
- A missing requested hour yields an empty row for every site, count 0, expected count 1 and `missing_hour`. No missing label becomes zero. Missing hours can also be outside the released span when explicitly requested.
- Duplicate, out-of-order, offset-bearing or non-hourly timestamps; mismatched volume/duration row clocks/lengths; ragged matrices; missing/duplicate/unmatched entity IDs; unknown schema; or missing/corrupt input cause **run-level failure**. No averaging, sorting, deduplication, rounding or silent ID intersection is used to repair them. Failed outputs must not be consumed.
- Volume and duration columns are joined by IDs, allowing different column order. Every site in metadata is retained; no activity/capacity threshold is applied.
- Duration is a companion **diagnostic only**. Invalid duration, positive volume with zero duration and zero volume with positive duration are counted and sampled in `qc.json`; they do not invalidate an otherwise valid energy value. The publisher may have processed these variables separately; no physically exact proportionality is imposed without evidence.
- Member-count discrepancies in site metadata are diagnostics. Unknown charger memberships or inconsistent city/site/charger identities fail structural validation.
- Pricing/weather/POI/distance are not model features or acceptance filters in this adapter. Prior inventory remains the source for their diagnostics. The adapter reads five members per city: volume, duration, sites, chargers, info.

`file_valid_mask` is neither an `observed_mask` nor a forecasting-eligibility mask. Original observation/imputation history remains unknown. #18 must distinguish historical-X masking from Y validity, preserve missing Y and follow forecast→store→label availability→score→update. Full-stream QC statistics must not choose forecast origins/cohorts using future labels.

## Explicit metadata overrides, leaving raw unchanged

- In `sites.csv` and charger membership fields, recognize only the observed `site_id` / `site` aliases. Record the original field name; output identity uses `entity_id`.
- AMS/JHB `info.csv` has the normal nine-field header.
- LOA/MEL/SPO/SZH has the exact known eight-name header containing `total_siteBSCAN_eps`, with nine row values. The adapter applies an **in-memory named override** to the documented nine-field layout. It requires the exact recognized header, one nine-value row, matching city code and matching site/charger counts from their own tables, and a finite positive clustering radius. Unknown defects fail instead of guessing a mapping.
- Original/effective header arrays, override status, alias fields, source members and validation rationale are recorded in each city QC report. No raw CSV or ZIP member is rewritten. Static activity totals are not emitted as model features or used for selection.

## Clock and provenance limits

`--clock-policy publisher-local-naive` and `--interval-label start|end` are required. No default timezone/UTC conversion, DST inference or offset attachment is applied.

- `start`: label t represents nominal `[t,t+1h)`.
- `end`: label t represents nominal `[t-1h,t)`; output is shifted back one nominal hour to label the bin start.
- Requested `--start` inclusive / `--end` exclusive are whole-hour offset-free boundaries in each city's published local-label grid.

The evidence run explicitly chooses **start labeling as a provisional assumption**, not a verified meter/label-arrival fact. The paper supports city-local time intent but exact original bin/arrival/DST conventions remain unresolved. The profile preserves the release's nominal 24-label days and does not claim correct absolute-time durations during DST transitions. No consumer may attach UTC and call that verification. #18 must carry this assumption into chronological-release replay; stronger clock/causality claims require new evidence/review.

Three distinct states remain:

| State | Meaning after this adapter |
| --- | --- |
| File-valid | Per-row released energy passes this contract's structural/numeric checks |
| Forecasting-eligible | Pending #18 windows, permitted-history splits/scaling, origin and label policies |
| Strict-online-ready | Not established; publisher imputation and availability lineage remain unresolved |

Manifest `strict_online_ready=false` means **not certified**, not a measured finding that every value leaks. `analysis_group` records `other_geographies` or `shenzhen_later_period` for reporting; it is not a new training split or cohort filter.

## Execution / acceptance

```sh
python -B -m tools.charged_hourly \
  --output-root data/processed/charged \
  --run-id YOUR_NEW_RUN_ID \
  --start 2023-04-01T00:00:00 \
  --end 2023-10-01T00:00:00 \
  --interval-label start \
  --clock-policy publisher-local-naive
```

Use Python 3.12, optionally `--storage-root /path/to/storage` with catalog layout. Standard archive only; no `remove_zero` selection or city/site-selection option. Every run uses a new directory; raw storage and existing directories are refused. Large hourly CSVs are machine handoff files, not Excel workbooks; read the small QC/manifest/report for review.

The source archive is freshly verified against size/SHA-256/publisher MD5. ZIP streams check member CRC while read; archive identity binds the member bytes. Record code commit/hash/worktree state, config, run ID, Python/platform, UTC start/runtime, input member sizes/CRCs, per-city counts/overrides/diagnostics, and output size/SHA-256. Partial failed runs remain as evidence with failed status; completed city files inside one do not make it accepted.

Exit 0 means technical output completion under these rules, with diagnostic anomalies still possible. Exit 1 means validation/read failure; argparse usage errors return 2. The accepted bounded research scope does not substitute for peer review of this implementation or #18 acceptance. No model effectiveness or independence claim follows from a passing run/test suite.
