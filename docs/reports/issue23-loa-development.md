# LOA Development: complete canonical comparison

[Published analysis/evidence bundle](https://drive.google.com/file/d/1KUX_yyOyP8adddzXP2BSmEzKFfJFIc_K/view), 862,137 bytes, SHA `5cae69c0d58856ecf44f3f6a122e639f6a4373eddad035c5530d9c71a0761804`. Root fresh native byte/SHA/ZIP-CRC and all 34 manifest-file checks passed. Raw dependencies remain external as specified below.

Issue #23; own Qyroven artifacts, reviewed 2026-10-27. All 27 declared station/history-budget/seed units and 378 method cells are externally accepted by the root coordinator. The new canonical view passed fresh CPU daily/latest-state and saved-cost integrity checks. This report describes the selected Development cohort; it does not establish scientific superiority, population effectiveness, independent peer approval or Final readiness.

## Scope and provenance

Canonical root: `runs/issue23-loa-development-canonical-27-20261027-v1`. Ledger 42 SHA `9db282d6cb2940eb9b33838553d4605665f5c71dffcec07154a5ab04d54347bb` selects accepted retained or explicitly migrated invocations using receipt/catalog/proof/report hashes. It does not select by outcomes. Older duplicates remain preserved; the canonical symlink view is not itself a portable raw export.

Each whole unit includes all 14 methods with predeclared method-specific configurations, matched input/runtime and exact shared issued/scored origins. Budgets are 7/14/28 days, seeds 42/43/44, unchanged 24→24 task and 90 replay days. The prefix count-rank/hash cohort has three stations per budget, with no empty-prefix targets.

| Budget | Station IDs | Initial training examples per station | Scored stations |
|---|---|---:|---:|
|7 days|201,164,186|6|3|
|14 days|216,161,154|13|3|
|28 days|91,33,10|27|3|

Station populations differ across budgets; their aggregate difference is not a controlled history-budget effect. Publisher-local-naive clocks and deployment `2023-07-01T00:00:00` are preserved. Publisher preprocessing/imputation and true availability-clock limitations remain. Raw archives were not freshly downloaded by this review.

Frozen primary analysis SHA `ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6` supplies Source epochs 10, controller recipe 1, Fixed lambda 1.0, Source-error 1, uncertainty 1, drift 3 and parameter-retention 2. `without_confidence` remains an alias for `online_best`. No city-specific tuning, method/loss/retention/controller change or Hung implementation adoption was introduced.

Every target uses its own seed’s original LOA Source. The resolver verified source-kit archive size/SHA/CRC and exact report/checkpoint/sidecar bytes, then CPU-loaded all three Sources to check model/optimizer, city/dataset/stage/population, seed/10 epochs, original-report metadata and finite nonnegative 64-dimensional latent scales. Target latent fingerprints agree where applicable. Source producer environments are preserved separately from target environments.

| Seed | Original LOA Source SHA-256 |
|---|---|
|42|`ca703dc98859cefc8ac9145a97970c0b0c2f083eb07fcc39d56fd417d3d1b419`|
|43|`31ee68e5ed021f4318b9fc1a239c30a914c8d2c8f3b40fabe2462cca43538086`|
|44|`1549235c7bbb948005bdd970cb4a04d8527639f5f5d22bffa44ff3143dd47b8e`|

Target producer environments are mixed:182 cells A100/PyTorch 2.11.0+cu130,154 cells T4/cu130 and 42 cells T4/cu128. All 14 methods share an environment within each unit, but stations/budgets/seeds can use different hardware. Source provenance remains its original producer context. All identified core hashes match despite producer Git envelopes `b85c15165c810a2be5332f030d739c0c59971cce` and `aa9f91cdc828e0d48c693a26b306208ec41de640`; canonical assembly/analysis records commit `3a43ece87da9a7ff366a3a137f0389ff980e0b73`. These mixed timings cannot establish hardware speed or city speed comparisons.

## Fresh verification and descriptive results

Fresh daily verification covers 378 runs and 69,930 hashed files, with 3,630 audit forecast scores. All 378 latest states passed independent verification. Saved report costs/steps exactly match serialized state and event reconstruction:72,900 candidate steps,3,630 audit steps and 972 initial adaptation steps. No training/inference or timer remeasurement was performed.

There are 34,020 scheduled, issued and scored method-days, zero null cells and 90 scored days for every method/unit. These repeated method-day counts are not independent samples. Actual origins are identical within units and paired seeds. The analysis averages days within period, paired seeds within station, then weights stations equally; it does not fill labels or intersect favorable days.

| Budget | Adaptive MAE | Target-only MAE | Fixed retention MAE | Adaptive minus Fixed | Exploratory 95% paired interval |
|---|---:|---:|---:|---:|---|
|7 days|1.2372|1.8831|1.2105|+0.0267|[-0.0393,+0.1390]|
|14 days|2.3160|3.2922|2.2981|+0.0179|[-0.0305,+0.0869]|
|28 days|2.8183|4.7006|2.6453|+0.1730|[-0.2030,+0.8168]|

All values are kWh. Adaptive has lower observed mean MAE than Target-only and higher observed mean MAE than Fixed retention in each budget. Every Adaptive-minus-Fixed interval crosses zero; neither equivalence nor superiority follows. Adaptive’s station-level negative-transfer rate against Target-only is 0/3 in each budget, conditional on these selected stations and seeds. Seasonal naive also has lower observed city mean MAE than Adaptive in the 7-day and 28-day cohorts. The full 14-method table prevents a favorable comparator-only reading.

| Method |7-day MAE|14-day MAE|28-day MAE|
|---|---:|---:|---:|
|adaptive|1.2372|2.3160|2.8183|
|block 28|1.2232|2.3160|2.8549|
|block 7|1.2180|2.3203|2.9390|
|drift|1.2068|2.3143|2.7638|
|fixed_retention|1.2105|2.2981|2.6453|
|frozen_source|1.2995|2.5495|3.1052|
|full_finetuning|1.2629|2.3279|2.9182|
|online_best|1.2112|2.3206|2.7316|
|parameter_retention|1.2657|2.3278|2.9186|
|seasonal_naive|0.9842|2.7403|1.8591|
|source_error|1.2025|2.3159|2.7845|
|target_only|1.8831|3.2922|4.7006|
|uncertainty|1.2287|2.3160|2.8513|
|without_source_initialization|1.9787|3.3826|4.8761|

Adaptive-minus-Target-only exploratory 95% intervals are [-1.3551,-0.1660], [-2.1968,-0.2100], [-5.1425,-0.3549]. Resampling is unchanged:2,000 draws,7-day circular calendar blocks, alpha 0.05, seed 20261026; common calendar draws are shared across sampled stations and paired seeds are averaged conditionally. No bootstrap replicates are undefined. Three nonrandom/possibly colocated stations, calendar seams/nonstationarity, Development calibration and no simultaneous-comparison correction preclude population-confidence or calibrated predictive-coverage claims. No subgroup intervals are estimated.

Weekday/weekend, fixed days 1–30/31–60/61–90, prefix load-density and initialization strata remain in the summary. Proxy associations compare same-block available signals with candidate error gaps; they do not demonstrate next-block prediction or causal retention benefit. Switching retains decision opportunities, missing outcomes and drain-only boundaries. There are 265 finalized isolated audit summaries, all with paired gaps; this is not a harmful-switch rate or guarantee that every last-block audit finalized. Shared definitions remain in `docs/reports/issue23-analysis-extensions.md`.

## Cost scope and reporting revision

Selected target producer elapsed spans sum to 2796.175684 seconds. The three original ten-epoch Source trajectories total 101.381746 seconds and 5,790 optimizer steps, counted once across reuse. Canonical matrix wall time is null: this assembled collection has no single invocation timer. Component timers are subsets of target elapsed, never additive extras. Source elapsed includes latent-scale/checkpoint work; target elapsed includes Source/ensemble loading, adaptation, replay and serialization.

Recorded inference/update counters include all active candidate branches; initial adaptation occurs once before cloning. Audit inference/update seconds and steps are separate. Per-lambda seconds/VRAM, audit clone/serialization-only overhead and incremental audit VRAM are not separately measured; GPU peaks are process peaks. Mixed hardware, concurrent activity and different units prevent controlled runtime comparisons. Historical tuning, retries, lost attempts, idle allocation, staging, export/transport, external verification and review are not comprehensively timed. No full project bill or deleted storage peak is claimed.

Original approved analysis remains untouched in `analysis/`. Reporting-only `analysis-reporting-v2/` relocates the historical 690-cell calibration count, corrects stale uncertainty prose and records the completed canonical verification status. All 47,235 original numeric values, frozen choices and run CSV bytes are exactly unchanged. No bootstrap, metric, threshold or scientific choice was recomputed by the reporting revision.

The bundle includes summary/CSV, invariance, fresh proofs, Source/input/code identities, plot, scripts and a selected-run→accepted-receipt→catalog/part restoration manifest. Raw inputs/labels, tensors, symlink trees and large raw archives remain external dependencies; covering parts may overfetch unselected runs. Existing archive commitments are referenced, not represented as a new full binary rehash. Independent replay requires restoring exact original Source/raw parts and fresh safe byte/SHA/CRC/daily/latest checks. The exporter’s symlink guard remains intact.

README-wide tests/lint were not rerun for this ignored artifact/reporting work; fresh scientific artifact verification, cost-state checks, numeric invariance and inspected plotting are the relevant checks. Artifact authoring used no cloud publication, Git/ledger mutation, new fits or Final values; root subsequently published the verified bundle above. Root acceptance and peer scientific review remain distinct.

## Artifact pins

| Artifact | SHA-256 |
|---|---|
|`study/matrix.json`|`be8d4233f7ba668591c866b28db7b42b572d097c54643a727338bd10fee7e6cd`|
|`independent-daily.json`|`3a84018ccaffa00500256bcfdf2be8ba114ab59e123018827c73dd7e31968197`|
|`independent-states.json`|`5eb4fc958791ce9a515b4da6eaaff8d0c569d36d004f06b636771794d3921956`|
|`cost-integrity-v1.json`|`a94dbce3ecb6df3f982d68efa990edbe2faf11aea52b9a75da034bd5c01ec080`|
|`analysis/summary.json`|`cfdc5b20818deedd169431fed88d697f186268d4f18e7c87449ccd0145303720`|
|`analysis-reporting-v2/summary.json`|`a01e82c212ea7eb6626d4589bfdcefe7fdb13fea86af1c719bfb3d5d69ce38bf`|
|`analysis-reporting-v2/reporting-invariance.json`|`ecc60b934730fe9ea04147f01520c47c7a32f1f33af46b0c71fb939c6c5d795b`|
|`analysis-reporting-v2/runs.csv`|`0c200aac6464e0ca8b3b07ebd6c3c672c1aa09659889767ac70b8b25d475b568`|
|`analysis-reporting-v2/loa-descriptive-v1.png`|`7cf3004b260888959309d8585f9e692df6702e34ca03b2bc25723d84d6f246be`|
