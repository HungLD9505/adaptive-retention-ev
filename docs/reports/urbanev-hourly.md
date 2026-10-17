# UrbanEV hourly processing and QC — issue #16

## Scope and status

Implemented on `feat/16-urbanev-hourly`: `tools.urbanev` (source verification, run orchestration and evidence) and `tools.urbanev_hourly` (station-level aggregation/QC). [Contract and reproduction command](../data/HOURLY_CONTRACT.md). [Machine-readable evidence](urbanev-hourly-issue16.json).

This is a technical handoff for peer review, **not completed model-input processing or approved research data**. The original Report 1 and catalog are unchanged. No raw input was overwritten, imputed or deleted. The issue remains open pending contract/time-assumption review and acceptance.

## Decisions requiring review

- Minimal shared keys: dataset/city/entity/hour, estimated energy, file-valid mask, constituent counts and reasons. `file_valid_mask` is not an original-observation mask.
- Sum publisher-derived five-minute `volume` directly. Twelve unique on-grid finite nonnegative volume AND duration observations are required; invalid hours retain rows with empty energy and mask 0. Zero energy remains valid when those conditions pass.
- Pricing, occupancy and static-capacity anomalies are logged; no data-fitted outlier deletion, station exclusion, zero-sequence removal or prorating. Static capacity is not inferred from inconsistent infrastructure metadata.
- The run explicitly uses **Asia/Shanghai, start-labeled intervals**, `[2022-09-01, 2023-03-01)`. These are provisional assumptions because the exact upstream interval generator is unavailable. `end` labeling is implemented/tested as an alternative. The output's +08:00 is attached under the stated assumption, not proof of source-clock conversion.
- Real label arrival and upstream original-observation status remain unknown. No strict-online, physical-meter-accuracy or effectiveness claim is made.

## Actual run

| Item | Result |
|---|---|
| Run ID | `issue16-start-v1-20261017` |
| Executed code commit | `5e7778a8cd783a483f153bfa599a7d0a0e25d928` |
| Runtime | 244.55 seconds, Python 3.12.14 |
| Archive identity | SHA-256 / size PASS against catalog |
| Extracted identity | Every required metadata and station file matched ZIP member size/CRC; SHA-256 recorded per input |
| Stations processed | 1,682 |
| Source records scanned | 87,679,296 |
| Requested output hours | 7,306,608 (4,344 per station) |
| File-valid hours | 5,745,899 (78.64%) |
| Invalid hours, energy left empty | 1,560,709 (21.36%) |
| Stations with any valid hours | 1,661 |
| Stations with all 4,344 hours valid | 0 |
| Valid zero-energy hours preserved | 1,901,982 |
| Duplicate / off-grid / out-of-order records | 0 / 0 / 0 |
| Missing expected grid samples | 0 |
| Technical run status | `technical_qc_pass`; research acceptance remains `pending_peer_review` |

These are file-valid counts, not a selected research cohort. Complete input/label windows and deployment-prefix eligibility belong to #18. Full-period audit statistics must not be used to tune final-target exclusions.

## Metadata and diagnostics

There are **240 station/charger-count mismatches** and **82 nonpositive/nonfinite power entries** in the original metadata. Rated-capacity checks are unavailable for 240 stations. The station IDs are listed in the JSON evidence; no identifiers or powers were repaired.

Additional row-level counts (not automatic target filters): occupancy-count inconsistency 188,065; invalid occupancy counts 18,555,366; volume above reliable static rated capacity 5,976; duration above static charger capacity 679; zero/nonzero disagreement between energy and duration 39,805. Missing/negative field counts are retained in the JSON summary.

Infrastructure snapshots are not proven contemporaneous physical capacity. Passing the structural run and finite-value rules does not resolve these anomalies. Their research treatment needs review, not silent clipping or deletion.

## Real output examples

| entity_id | timestamp | energy_kwh | file_valid_mask | valid_sample_count | qc_flags |
|---|---|---|---|---|---|
| 1001 | 2022-09-01T00:00:00+08:00 | 4.0833333333333321 | 1 | 12 |  |
| 1001 | 2022-10-27T16:00:00+08:00 |  | 0 | 7 | incomplete_hour;invalid_target_sample |

The empty invalid energy cell is intentional. It must not become a target zero when read by #18.

## Checks and practical limits

- 28 offline tests PASS on Python 3.12: aggregation with independently known sums; zero activity; missing/invalid labels; duplicate/off-grid/out-of-order clocks; start/end conventions and midnight; source/archive mismatch; inventory and unsafe-output failures; immutable inputs, new-run protection and deterministic output; nonzero exit with failed QC evidence. No fixture downloads real data.
- Full actual output checked independently for key/time ordering, mask/empty-energy invariants, constituent counts and per-station counts/energy totals.
- All 4,344 hours of station 1001 independently grouped from source using Decimal arithmetic: 3,447 valid / 897 invalid; output sums and masks matched. This checks numerical implementation, not source energy truth or interval causality.
- README source listing, Ruff lint/format, diff checks and raw archive verification PASS. PR CI covers Ubuntu and Windows; see the exact final PR head for its result. The full run was local, not a Windows actual-data reproduction.
- Only standard-library code is required. IANA zones need system timezone data or the `tzdata` fallback on a machine without it; offline CI uses UTC fixtures. Offset-transition windows are rejected rather than guessed.
- The local run has a manifest, full station QC and ~millions of CSV rows outside Git. The small JSON evidence stores artifact hashes and lineage. To reproduce, run the documented command with a **new** run ID using the executed commit/source hashes; then compare hourly bytes and QC counts. Runtime/manifest timestamps naturally differ.

## Handoff to #17 / #18

Review the shared contract and provisional clock assumptions before accepting these outputs. #17 audits CHARGED independently and supplies only released-file validity, not an invented observation mask. #18 handles reviewed source/development/final separation, permitted-prefix scaling, 7/14/28-day histories, calendar/masks, 24→24 windows, loader and leakage tests. None of those are implemented by #16. Any unresolved source/clock limitations must carry forward into claim scope.
