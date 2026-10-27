# JHB Development: recovered complete comparison

Issue #23; own Qyroven artifacts, reviewed 2026-10-27. The recovered JHB collection
contains all 27 declared station/history-budget/seed units and 378 method cells.
Existing off-runtime daily/state proofs and portable restoration cover the entire
collection. A new read-only review verified their identities, all run reports,
unchanged recipes and three original JHB Sources. No refitting, city-specific
tuning, Hung implementation adoption, Final access, population-effectiveness
claim or peer scientific approval is implied.

## Scope, provenance and recovery

Run root: `runs/issue23-jhb-complete-recovery-20261026-v2`. Each unit contains all
14 methods; budgets are 7/14/28 days and comparison seeds are 42/43/44. The
unchanged task is 24→24 with 90 replay days. Cohort selection uses initial-prefix
count-rank bins and hashed identity within the declared ready Development
population, not replay errors. All selected JHB stations have initial training
examples; there is no empty-prefix/source-only target in this collection.

| Budget | Selected station IDs | Initial examples per station | Scored stations |
|---|---|---:|---:|
| 7 days | 26, 44, 33 | 6 | 3 |
| 14 days | 33, 4, 12 | 13 | 3 |
| 28 days | 37, 44, 26 | 27 | 3 |

Budget populations differ. Comparing their aggregate errors does not identify a
controlled history-budget effect. JHB uses the unchanged publisher-local-naive
clock and deployment `2023-07-01T00:00:00`; no UTC collection/availability semantics
are invented. Publisher preprocessing/imputation and true availability-clock
limitations remain. Raw archives were not freshly downloaded or reverified by
this review; catalog fingerprints do not constitute fresh-download evidence.

Frozen choices come from primary analysis
`ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6`:
Source epochs 10, controller recipe 1, Fixed lambda 1.0, and proxy recipes Source
error 1, uncertainty 1, drift 3 and parameter retention 2. The
`without_confidence` alias remains `online_best`. Exact city configurations and
input bindings pass the existing `validate_collection`/`validate_matrix` checks;
no method, loss, retention, history budget or controller change was introduced.

All 14 executed names are `adaptive`, `block28`, `block7`, `drift`,
`fixed_retention`, `frozen_source`, `full_finetuning`, `online_best`,
`parameter_retention`, `seasonal_naive`, `source_error`, `target_only`,
`uncertainty` and `without_source_initialization`.

Every target identifies its own seed's original JHB Source, never UrbanEV weights.
Fresh independent CPU loads checked all three checkpoint hashes, model/optimizer
integrity, source dataset/city/stage/population, seed/10-epoch metadata, original
report consistency and finite nonnegative 64-dimensional latent scales. Non-null
target latent bindings match the corresponding Source scale fingerprint.

| Seed | Original JHB Source SHA-256 |
|---|---|
| 42 | `73b1d6b8a2d4466d83b5cf207d161dc0c101adfd02af3515a56c960b230009eb` |
| 43 | `86e40cce4414876fa319e0f74a76996d6f3f0ad72d89bd98d53cdedcb7c0439e` |
| 44 | `e0deaabf8f9d8e63341ddc99d69e2eb2b5b7225a968fa5e53e4cabc595dc96c1` |

All 378 target rows use the same recorded T4/PyTorch 2.11.0+cu128 environment;
within-unit environment/input identities agree across all methods. This is not a
mixed-hardware JHB comparison. Hardware/runtime differences from UrbanEV, other
cities or later A100 work cannot support controlled speed comparisons. Executed
matrix code commit is `9057364e6a8e663b9ba9c204621d109c02bed3e0`; local analysis
records `cd3a95279c98e2b35cddbaa679d8f13118a63d4b`. All identified research core
file hashes match the current checked implementation despite Git-envelope changes.

## Verification and descriptive results

Existing full off-runtime verification covers 69,930 hashed daily files, 5,791
independently checked audit forecast scores and 378 latest target states. The
portable-restoration test's daily/state proofs are byte-identical to these full
proofs. Earlier metadata-only evidence mentioning 182 restored rows is historical
and superseded by the complete proofs; it must not be presented as the final
scope. The local analysis equals the server analysis in every field except the
declared analysis-commit and verification-envelope identities; run CSV bytes
match. The new review checked all 378 report fingerprints against analysis lineage.

There are 34,020 scheduled, issued and scored days across method cells, with
zero null cells. All 27 units retain 90 scored days per method. Existing analysis
requires identical actual issued/scored origins across methods and identical
scored origins across paired seeds; it never intersects favorable days or fills
missing labels. A period averages daily MAE/MSE before its RMSE root, then paired
seeds are averaged within station and stations receive equal weight.

| Budget | Adaptive MAE | Target-only MAE | Fixed retention MAE | Adaptive minus Fixed | Exploratory 95% paired interval |
|---|---:|---:|---:|---:|---|
| 7 days | 3.5241 | 5.6146 | 3.2689 | +0.2553 | [-0.0291, +0.6151] |
| 14 days | 1.3615 | 2.2674 | 1.3332 | +0.0283 | [-0.0339, +0.1475] |
| 28 days | 2.0480 | 3.4209 | 1.9969 | +0.0511 | [-0.2842, +0.5389] |

All values are kWh. Adaptive has lower observed mean error than Target-only and
higher observed mean error than selected Fixed retention in each budget. Every
Adaptive-minus-Fixed exploratory interval crosses zero; this does not establish
equivalence or superiority. Adaptive's station-level negative-transfer rates
relative to Target-only are 0/3, 1/3 and 0/3. The 14-day population therefore
contains an actual station whose paired-seed mean error is worse than Target-only,
despite the lower city macro mean.

Adaptive-minus-Target-only intervals are [-3.0374, -1.1637], [-2.3304, +0.0074]
and [-2.7837, -0.1731]. Bootstrap settings remain 2,000 resamples, 7-day circular
calendar blocks, alpha 0.05 and seed 20261026. The same calendar draws are shared
across sampled stations; seeds are averaged conditionally. No reported replicate
is undefined. Only three nonrandom/possibly colocated stations per budget,
calendar seams/nonstationarity, conditional Development selections and no
simultaneous-comparison correction prevent population-confidence or calibrated
predictive-coverage claims. No subgroup uncertainty intervals are estimated.

The summary retains weekday/weekend, fixed calendar phases 1–30/31–60/61–90,
prefix load-density and initialization strata. Proxy correlations describe
same-block available signals and candidate error differences, not next-block
prediction or causal retention benefits. Switching retains opportunity counts,
missing outcomes and drain-only boundaries. There are 412 finalized isolated
audit summaries, all with non-null paired gaps; this neither guarantees every
last-block audit finalized nor defines a harmful-switch rate or recovery time.
See the [shared analysis definitions](issue23-analysis-extensions.md).

## Cost, reporting revision and remaining limits

Recorded JHB matrix invocation time is 2,540.6472 seconds; the encompassing training
subprocess stage is 2,543.8407 seconds. Selected Source training elapsed totals
15.7790 seconds, counted once across reuse. Those scopes overlap: do not add the
Source total to the whole invocation or add component timers to target elapsed.
Source elapsed already includes latent-scale estimation/checkpoint work; target
elapsed includes Source/ensemble loading and replay serialization. Caller input
preparation, earlier failures/recovery, export, transfer, external verification
and review are not a comprehensive project-total timer. The recovered verification
stages record 21.1061 seconds daily, 16.2145 seconds states and 53.8113 seconds
analysis; these are identified stage timings, not a fresh runtime benchmark.

New `analysis-reporting-v2/` preserves the original `local-analysis/` and changes
only reporting metadata. It relocates the historical 690-cell primary calibration
count, corrects stale uncertainty prose and updates the historical statement that
off-runtime verification was pending. Exact comparison preserves 47,437 original
numeric values, all frozen decision values and byte-identical run CSV. No metrics,
bootstrap choices/results or scientific thresholds were recomputed.

The new review CPU-loaded Sources and checked metadata/report/proof hashes; it
did not rerun the already complete daily/state verification or independently
re-execute controller statistical decisions. Existing proof scopes do not prove
publisher causality, scientific validity, true collection clocks or independent
peer approval. No Final values, training, cloud publication or Git/ledger mutation
were used in this report task. README-wide tests/lint were not rerun for this
reporting-only artifact work; numeric invariance, bundle hash/CRC checks and
visual inspection passed.

## Local artifact identities

Small standalone result bundle:
`runs/issue23-jhb-complete-recovery-20261026-v2/jhb-development-analysis-v1.zip`
(518,240 bytes). It contains revised summary, all run rows, lineage, review,
reporting invariance, existing daily/state/acceptance proofs, provenance, manifest,
plot source and inspected PNG. Raw inputs/labels, tensors, symlink run trees and
large daily evidence are excluded. The bundle supports result inspection, not
full independent replay; it has not been newly published by this task.

| Artifact | SHA-256 |
|---|---|
| Canonical recovered matrix | `2a87b2120e7e9ccccd8c658c8a4fd34f21707b6d7a0e9c4d1d87aaaee2b053a7` |
| Full local daily proof | `d6d26fcb60e399a6f2b93e940935e9f8971b2942e0559532e2483ac75cbf6476` |
| Full latest-state proof | `8e9ece527392b9df9ab1972fa1f9fd3f44ddec5ae20f7c05a785b4ea6a60ab08` |
| Original local summary | `59c424c192bf224364fa8afb46c4cbde1a221900f6effa3eec86ea8ab0f204ae` |
| Revised reporting summary | `8eabbf1f6527dec5402adb0ff1db6bf06d4cd6ebcdc3c3f086a1cb4a435061c6` |
| New independent review | `50c88597c1c904c85768abc3d28d4c78077a086ee4af3d81e5565128523c5a94` |
| Reporting invariance | `c2f4acd863869b0c5e75ce5a433ef82b2d31622f2d4a11773553c533bb1ad4eb` |
| Run CSV | `8b1fba2478516a83f1c161c52811edc2955fc5a5a7492232d8fbecfb26f2f96e` |
| Small result bundle | `7ef3c9a1c0b234ce0ead46e257c14d4fd8c6a0c12dd45d1343c047db0d11d851` |
| Bundle manifest | `7744a36d5cec1aab110399ad42eb6fad1966cf4fdf46847bef701907c5ab634a` |
| Descriptive PNG | `6be7931af0636b1cf676ea6f56fb0222219b8fe0288e849ddc6c7bea5704dd50` |

The [published standalone JHB analysis bundle](https://drive.google.com/file/d/12jNGqCFEO0eAKUdnke85Oj6gJvSrHN0t/view) is518240 bytes, SHA `7ef3c9a1c0b234ce0ead46e257c14d4fd8c6a0c12dd45d1343c047db0d11d851`. Fresh native Drive download matched exact local bytes and passed ZIP CRC. This verifies publication of the reviewed analysis; it does not turn exploratory intervals into population-effectiveness evidence.
