# Issue #18 — real-data loader trial

## Outcome

Ran the unchanged development loader on all 1,682 UrbanEV station IDs and 4,280 standard CHARGED site IDs for budgets 7/14/28: **21 runs**, with 17,886 entity/budget records. These are 5,962 dataset-scoped IDs, not 5,962 verified distinct physical locations. No merge, model training, official cohort selection or effectiveness evaluation occurred.

**18 CHARGED runs reached technical success. All three UrbanEV runs are incomplete because some permitted prefixes have no valid available energy from which to fit a scaler.** Their retained outputs/counts are diagnostic review artifacts, not accepted model inputs. No entity was reassigned, filled or silently excluded.

“Trainable” below means the implemented gate: an identified positive prefix scale and all 24 valid/available labels within the permitted prefix. Historical X can be masked. This is file/protocol eligibility under declared assumptions, not scientific acceptance or strict-online certification.

## Fixed trial settings

- Loader source revision: `50ae029efa53e9c98d16bbac34fd9225d5f77db8`, byte-equivalent to the PR #34 loader snapshot `8fd69b2`. Runtime code was not changed for these runs.
- Fixed review salt: `ev-input-review-v1`, declared before inspecting the counts; no reroll, tuning or alternate split was tried. This is not an official production salt.
- Availability: hourly-bin end + **0 hours**, explicitly assumed. Actual arrival and publisher upstream causality remain unverified.
- UrbanEV: source history starts 2022-09-01, deployment 2022-12-01, replay through 2023-02-28 (90 daily origins), constant `+08:00` assumed local clock.
- CHARGED: source history starts 2023-04-01, deployment 2023-07-01, replay through 2023-09-30 (92 daily origins), publisher-local naive clock; no UTC/DST invention.
- Each city/dataset is separate. No cross-city/cross-dataset pretraining pool is created. UrbanEV stays primary; CHARGED supplementary, SZH later-period reporting separate.

## Entity inventory

| Dataset | City | IDs | Source | Development | Final | Source IDs with initial samples |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| urbanev | SZH | 1,682 | 981 | 328 | 373 | 871 |
| charged | AMS | 2,449 | 1,496 | 475 | 478 | 1,496 |
| charged | JHB | 47 | 26 | 8 | 13 | 26 |
| charged | LOA | 229 | 137 | 51 | 41 | 137 |
| charged | MEL | 63 | 34 | 14 | 15 | 34 |
| charged | SPO | 47 | 29 | 8 | 10 | 29 |
| charged | SZH | 1,445 | 886 | 288 | 271 | 886 |

The role assignment is identical across budgets. Source samples/scales are identical across budgets because their source pre-deployment fit interval is unchanged. Source entities with no complete initial sample remain counted as source IDs, not relabeled.

## Initial training samples by budget

| Dataset / city | Budget days | Source samples | Development samples | Final samples | All roles | IDs with undefined scale | Targets with no initial sample |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| urbanev / SZH | 7 | 65,888 | 1,684 | 1,974 | 69,546 | 134 | 91 |
| urbanev / SZH | 14 | 65,888 | 3,644 | 4,275 | 73,807 | 131 | 90 |
| urbanev / SZH | 28 | 65,888 | 7,481 | 8,746 | 82,115 | 122 | 85 |
| charged / AMS | 7 | 134,640 | 2,850 | 2,868 | 140,358 | 0 | 0 |
| charged / AMS | 14 | 134,640 | 6,175 | 6,214 | 147,029 | 0 | 0 |
| charged / AMS | 28 | 134,640 | 12,825 | 12,906 | 160,371 | 0 | 0 |
| charged / JHB | 7 | 2,340 | 48 | 78 | 2,466 | 0 | 0 |
| charged / JHB | 14 | 2,340 | 104 | 169 | 2,613 | 0 | 0 |
| charged / JHB | 28 | 2,340 | 216 | 351 | 2,907 | 0 | 0 |
| charged / LOA | 7 | 12,330 | 306 | 246 | 12,882 | 0 | 0 |
| charged / LOA | 14 | 12,330 | 663 | 533 | 13,526 | 0 | 0 |
| charged / LOA | 28 | 12,330 | 1,377 | 1,107 | 14,814 | 0 | 0 |
| charged / MEL | 7 | 3,060 | 84 | 90 | 3,234 | 0 | 0 |
| charged / MEL | 14 | 3,060 | 182 | 195 | 3,437 | 0 | 0 |
| charged / MEL | 28 | 3,060 | 378 | 405 | 3,843 | 0 | 0 |
| charged / SPO | 7 | 2,610 | 48 | 60 | 2,718 | 0 | 0 |
| charged / SPO | 14 | 2,610 | 104 | 130 | 2,844 | 0 | 0 |
| charged / SPO | 28 | 2,610 | 216 | 270 | 3,096 | 0 | 0 |
| charged / SZH | 7 | 79,740 | 1,728 | 1,626 | 83,094 | 0 | 0 |
| charged / SZH | 14 | 79,740 | 3,744 | 3,523 | 87,007 | 0 | 0 |
| charged / SZH | 28 | 79,740 | 7,776 | 7,317 | 94,833 | 0 | 0 |

**Do not pretrain on the All roles column.** Source records feed source pretraining; each target’s records feed its own adaptation. Nor should repeated source records across the three budget runs be added as unique training data. Every 24→24 sample belongs to one entity.

## Replay inputs and labels

| Dataset / city | Budget days | Requested origins | Created inputs | Complete label days | Missing label days | All-missing X histories |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| urbanev / SZH | 7 | 63,090 | 57,060 | 45,416 | 11,644 | 8,359 |
| urbanev / SZH | 14 | 63,090 | 57,330 | 45,490 | 11,840 | 8,538 |
| urbanev / SZH | 28 | 63,090 | 58,140 | 45,789 | 12,351 | 9,024 |
| charged / AMS | 7 | 87,676 | 87,676 | 87,676 | 0 | 0 |
| charged / AMS | 14 | 87,676 | 87,676 | 87,676 | 0 | 0 |
| charged / AMS | 28 | 87,676 | 87,676 | 87,676 | 0 | 0 |
| charged / JHB | 7 | 1,932 | 1,932 | 1,932 | 0 | 0 |
| charged / JHB | 14 | 1,932 | 1,932 | 1,932 | 0 | 0 |
| charged / JHB | 28 | 1,932 | 1,932 | 1,932 | 0 | 0 |
| charged / LOA | 7 | 8,464 | 8,464 | 8,464 | 0 | 0 |
| charged / LOA | 14 | 8,464 | 8,464 | 8,464 | 0 | 0 |
| charged / LOA | 28 | 8,464 | 8,464 | 8,464 | 0 | 0 |
| charged / MEL | 7 | 2,668 | 2,668 | 2,668 | 0 | 0 |
| charged / MEL | 14 | 2,668 | 2,668 | 2,668 | 0 | 0 |
| charged / MEL | 28 | 2,668 | 2,668 | 2,668 | 0 | 0 |
| charged / SPO | 7 | 1,656 | 1,656 | 1,656 | 0 | 0 |
| charged / SPO | 14 | 1,656 | 1,656 | 1,656 | 0 | 0 |
| charged / SPO | 28 | 1,656 | 1,656 | 1,656 | 0 | 0 |
| charged / SZH | 7 | 51,428 | 51,428 | 51,428 | 0 | 0 |
| charged / SZH | 14 | 51,428 | 51,428 | 51,428 | 0 | 0 |
| charged / SZH | 28 | 51,428 | 51,428 | 51,428 | 0 | 0 |

Requested origins cover every configured target/day. Undefined scales prevent building some entities’ inputs and make those whole runs incomplete; the missing input count is not concealed as successful cohort selection. For entities with a defined scale, missing future labels never remove origins. Complete label days are recounted diagnostics only, not a criterion for choosing target IDs or forecasting dates. All-missing replay histories remain represented and flagged, as the proposed contract allows.

## Findings requiring review

### UrbanEV

| Budget days | No-scale Source IDs | No-scale Development IDs | No-scale Final IDs | Defined-scale targets with zero initial samples | Sparse positive prefixes with p95 = 0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 | 67 | 34 | 33 | 24 | 39 |
| 14 | 67 | 32 | 32 | 26 | 35 |
| 28 | 67 | 27 | 28 | 30 | 34 |

- 110 source IDs have no initial trainable samples: 67 undefined scales and 43 defined scales without a complete source label day. The resulting source pool has 871 IDs contributing 65,888 daily examples.
- Targets without initial trainable samples number 91 / 90 / 85 for 7 / 14 / 28 days. This includes undefined-scale cases plus defined-scale cases with no complete label day. A target input being constructible is not the same as having supervised initialization samples.
- Sparse positive prefixes with p95 = 0 occur in the real data. The proposed unit fallback preserves them, possibly at large normalized magnitudes; it is not evidence that the normalization is safe for training. These counts include source/target fit scopes for the selected budget.
- No counted initial trainable example has an all-missing X history under this trial’s bin-end availability assumption. Some replay histories are all missing and remain flagged.

### CHARGED

All released energy rows passed the existing file gate, so every contained daily candidate has complete Y and every created replay input has a complete released label day. This does not recover original/imputed masks or certify strict-online readiness.
All-zero fit prefixes are legitimate zeros under the file contract, not undefined scales. For example, AMS has 1,062 all-zero **fit-prefix** cases per budget, which is a different measure from the previously audited 1,061 all-zero full-release site series. Prefix lengths/roles differ, and the counts are not an inactivity classification. No all-zero site was excluded.

## Verification and files

- Processed hourly size/hash, known manifest profile, per-entity full grid, identities, validity/counts and finite energy were checked by every loader run. Raw archives were never modified and were not freshly re-verified here.
- Independent audit parsed all **26,104,368 original hourly rows** into daily valid/zero counts. It reconciled every entity/budget’s scaler population, zero-p95 status, contained candidate/trainable counts and replay-history flags with the loader; every replay label record was separately recounted.
- Spot-checked 63 real exported records across all 21 runs: prediction shapes/finite features, no future-label fields, matching label identity/origin, per-entity scaler identity, contained initial training and inverse units within 1e-6 relative/absolute tolerance. This is a spot-check, not a claim of parsing every serialized training record.
- Budgets were checked to preserve the same roles/source sample counts. Review aggregate counts do not reselect entities using future results.
- Existing fixture suite: **67 PASS** locally; Ruff lint/format and diff checks PASS. Routine CI continues to use fixtures only.
- Workbook QA: all four sheets rendered/visually inspected, no formula error matches, totals edit/recalculate/restore tested; native XLSX read-back confirms all 21 summary totals, all 17,886 detail rows, string IDs/numeric counts, five filter tables and frozen identity/header panes. Excel/Numbers UI was not opened. It is a fixed review snapshot; rerun loader/audit to refresh imported counts.
- Small committed evidence: [input-loader-real-evidence.json](input-loader-real-evidence.json). Large runs, per-entity JSONL and the formatted workbook remain local/ignored.

Local review files:

- `handoff/outputs/issue18-real-loader-v1-20261019/Loader_Review.xlsx` — Overview, Replay, Entities and Definitions; 17,886 entity/budget rows with filters and typed counts/IDs.
- `runs/issue18-real-loader-v1-20261019/configs/` — 21 explicit configs; `declaration.json` fixes the salt/availability before inspection; `execution.json` records exit status/runtime.
- `data/inputs/issue18-real-loader-v1-20261019/<dataset>-<city>-<budget>d/` — original new trial runs with forecasts/labels/training/entities/manifest.
- `runs/issue18-real-loader-v1-20261019/results.json` — independently reconciled summary/detail; `review-data.json` additionally records all-missing initial-history diagnostics.

To reproduce a loader run with an existing verified local producer output and the recorded config:

```sh
python -m tools.model_inputs \
  --config runs/issue18-real-loader-v1-20261019/configs/urbanev-SZH-7d.json \
  --output data/inputs/NEW-UNIQUE-REVIEW-RUN-ID
```

On a new machine, recreate the config from the fixed settings above and record the exact SHA-256 of its acquired producer manifest; file paths/producer outputs are outside Git. Do not replace a recorded expected hash to conceal different data. The producer manifest binds its hourly fingerprint. This trial did not rerun the raw→hourly producers.

## Acceptance boundary

#18 remains open. Do not merge, declare official input acceptance or hand these incomplete UrbanEV runs to the model consumer as successful runs. Team review must decide explicit prefix/eligibility handling, p95 fallback and scientific clock/arrival limitations before official cohorts. Any change requires review and new outputs, preserving these trial results. No method tuning was performed using Final.
