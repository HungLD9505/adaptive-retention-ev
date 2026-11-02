# AMS Development: complete canonical comparison

[Published analysis/evidence bundle](https://drive.google.com/file/d/1tp2O-up-enhnC8OzN4Z5OhMblXixUsOO/view), 918,925 bytes, SHA `d4d0ff99b8d0083cc390c83b017cfa86bafe04b53fca7f5b93d21f5a691ba2b7`. Root fresh native byte/SHA/ZIP-CRC and all 39 manifest-file checks passed. Raw dependencies remain external as specified below.

Issue #23; own Qyroven artifacts, reviewed 2026-10-27. All 27 declared station/history-budget/seed units and 378 method cells are externally accepted by the root coordinator. The new canonical view passed fresh CPU daily/latest-state and saved-cost checks. This is a descriptive Development handoff, without a superiority, population-effectiveness, independent peer-approval or Final-readiness claim.

## Scope and provenance

Root: `runs/issue23-ams-development-canonical-27-20261027-v1`. Exact ledger 46 SHA `5257cd9b6f987017b03e4a820e276252c4e8ed094949e04a8783847fc07eac7e` selects retained or explicitly migrated accepted invocations by receipt/catalog/proof/report identities, never outcomes. The collection uses its own retained original AMS Sources. Replacements are additional declared invocations, not recovery of original missing producer bytes. Old outputs remain preserved.

Each whole unit contains all 14 methods with predeclared method-specific configurations, matched input/runtime and exact shared issued/scored origins. The unchanged task is 24→24, history budgets 7/14/28 days, seeds 42/43/44 and 90 replay days. Cohort selection uses prefix count-rank bins and hashed identity within the ready Development population, not replay errors. There is no empty-prefix target in this cohort.

| Budget | Selected station IDs | Initial examples per station | Scored stations |
|---|---|---:|---:|
|7 days|1200, 1359, 1515|6|3|
|14 days|1349, 1441, 110|13|3|
|28 days|698, 1200, 2240|27|3|

Selected populations differ by budget; aggregate differences are not a controlled history-budget effect. Publisher-local-naive clocks and deployment `2023-07-01T00:00:00` remain unchanged; publisher preprocessing/imputation and true availability-clock limitations remain. Raw archives were not freshly downloaded or rechecked by this report task.

Frozen primary SHA `ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6` fixes Source epochs 10, controller recipe 1, Fixed lambda 1.0, and proxy recipes Source error 1, uncertainty 1, drift 3 and parameter retention 2. `without_confidence` remains an alias for `online_best`. No city tuning, method/loss/controller/retention change or Hung implementation adoption was introduced.

The three own-city Sources were bound to the published Source-kit archive bytes including full reports and costs, then CPU-loaded for model/optimizer, city/dataset/stage/population, seed/10-epoch metadata, original report consistency and finite nonnegative 64-dimensional latent scales. Non-null target latent fingerprints match the corresponding Source. Producer Source environment is preserved independently of target environment.

| Seed | Original AMS Source SHA-256 |
|---|---|
|42|`a368c3ebabeb9cb91180ff01ee41b271dbbdf888b610083834bbc75a5b2eda2d`|
|43|`14053287dbc260984dba17d2948dae26533b516aa16e3e3b25e74c3ab212e660`|
|44|`2354032b5314bbfcf81d5572474fe1513506d90e36abd1b36e5c6b82e37d35b7`|

Target environment counts: 126 cells: NVIDIA A100-SXM4-40GB, PyTorch 2.11.0+cu130; 56 cells: Tesla T4, PyTorch 2.11.0+cu128; 196 cells: Tesla T4, PyTorch 2.11.0+cu130. Within every unit all methods share the recorded environment, while different units can differ. All identified method/core file hashes agree despite producer Git-envelope differences: `aa9f91cdc828e0d48c693a26b306208ec41de640` (56 cells), `b85c15165c810a2be5332f030d739c0c59971cce` (322 cells). Analysis records clean commit `54fd9946e1cce1abddd4063982652e0e8609980e`. Mixed hardware, background work and different units prevent controlled speed comparisons.

## Verification and observed errors

Fresh daily verification covers 378 runs, 69,930 hashed files and 4,717 audit forecast scores. All 378 latest states passed. Report/state/event reconciliation passes 72,900 candidate steps, 4,717 audit steps and 972 initial adaptation steps. No training, inference or timer remeasurement was performed.

All 378 cells have 90 scored days and zero null metrics:34,020 scheduled, issued and scored method-days. Repeated method-day counts are not independent observations. Actual origins agree across methods and paired seeds; analysis does not fill missing labels or select favorable common days. Days are averaged within period, paired seeds within station, then stations receive equal weight.

| Budget | Adaptive MAE | Target-only MAE | Fixed retention MAE | Adaptive minus Fixed | Exploratory 95% paired interval |
|---|---:|---:|---:|---:|---|
|7 days|5.7605|0.5587|5.7486|+0.0119|[-0.0020, +0.0340]|
|14 days|25.4950|9.9177|25.4849|+0.0101|[-0.0995, +0.0828]|
|28 days|5.6233|3.8171|5.6047|+0.0186|[-0.0022, +0.0500]|

All errors are kWh. Positive gaps mean Adaptive has higher observed MAE. These are selected-cohort observations; a crossing-zero interval does not prove equivalence, and exploratory intervals do not establish population superiority. Adaptive station-level negative-transfer counts against Target-only are 2/3 (7 days), 1/3 (14 days), 1/3 (28 days). All 14 observed method means follow, including Seasonal naive; no favorable comparator subset is used.

| Method |7-day MAE|14-day MAE|28-day MAE|
|---|---:|---:|---:|
|adaptive|5.7605|25.4950|5.6233|
|block 28|5.7591|25.5178|5.6248|
|block 7|5.7509|25.4984|5.6151|
|drift|5.7497|25.4554|5.6352|
|fixed_retention|5.7486|25.4849|5.6047|
|frozen_source|5.7367|25.3446|5.5866|
|full_finetuning|5.7728|25.5020|5.6477|
|online_best|5.7504|25.4798|5.6224|
|parameter_retention|5.7731|25.5020|5.6477|
|seasonal_naive|0.0574|4.8751|1.3838|
|source_error|5.7497|25.4869|5.6170|
|target_only|0.5587|9.9177|3.8171|
|uncertainty|5.7961|25.4687|5.6494|
|without_source_initialization|0.6198|8.9003|3.5401|

Adaptive-minus-Target-only intervals for 7/14/28 days are [-0.1014, +8.0820], [-5.5328, +48.9382], [-3.5127, +7.8027]. Frozen bootstrap settings:2,000 draws,7-day circular calendar blocks, alpha 0.05 and seed 20261026; sampled stations share calendar draws, paired seeds are averaged conditionally. Undefined replicates: 0. Three nonrandom/possibly colocated stations per budget, calendar seams/nonstationarity, Development calibration and no simultaneous-comparison correction preclude population-confidence or calibrated predictive-coverage claims. No subgroup intervals are estimated.

The summary retains weekday/weekend, days 1–30/31–60/61–90, prefix load-density and initialization strata. Proxy relationships are same-block signal/error associations, not next-block predictions or causal retention benefits. Switching retains decision opportunities, missing outcomes and drain-only boundaries. There are 338 finalized isolated audit summaries, with 0 null paired gaps; neither harmful-switch rate nor recovery time is inferred. Definitions remain in `docs/reports/issue23-analysis-extensions.md`.

Adaptive has higher observed city mean MAE than Target-only, Fixed retention and Seasonal naive in all three budget cohorts. Station-level negative-transfer counts against Target-only are 2/3, 1/3 and 1/3 for 7/14/28 days. These adverse observations are retained; the cause and wider impact remain unresolved.

## Adverse seed/Source sensitivity retained

The complete predeclared AMS 1200/7-day group remains in the city collection. Its earlier focused analysis exactly matches all 42 canonical metrics, Source identities and commit chains. No adverse seed is dropped.

| Method | Seed 42 MAE | Seed 43 MAE | Seed 44 MAE |
|---|---:|---:|---:|
|adaptive|12.799506|0.336414|12.799506|
|fixed_retention|12.799506|0.274458|12.799506|
|target_only|0.844062|0.794008|0.685789|
|seasonal_naive|0.089383|0.089383|0.089383|

Prior authenticated Adaptive prediction ranges are seed 42: [2.2545485 e-10, 3.1230138 e-08] kWh; seed 43: [10.392755, 13.9017] kWh; seed 44: [3.1880585 e-10, 6.7670534 e-09] kWh. These prior observations are carried forward with matching producer commit chains, not newly inferred. Near-zero predictions for 42/44 and the different seed 43 result are adverse outcomes under the frozen budget. Tiny Adaptive/Fixed differences are not meaningful wins.

This is one station/budget, not a causal Source-quality experiment: Source/model/controller randomness varies together. The cause and wider impact remain unresolved. Full city means and every seed remain reported; no head/loss/epoch/checkpoint/seed/controller selection changed.

## Cost scope and reporting revision

Selected target process spans sum to 2961.750281 seconds. Three own Source ten-epoch trajectories total 1040.723658 seconds and 63,120 optimizer steps, counted once across reuse. Canonical matrix wall time is null: this assembly is not one invocation. Component timers are subsets, never additive extra cost. Source time includes latent-scale/checkpoint work; target spans include Source/ensemble loading, adaptation, replay and serialization.

Inference/update counters include all active candidate branches; initial adaptation is performed once before cloning. Audit inference/update seconds and optimizer steps are separate. Per-lambda seconds/VRAM, audit clone/serialization-only overhead and incremental audit VRAM are not separately attributed; memory peaks are process peaks. Mixed hardware prevents controlled benchmarks. Tuning, retries, lost attempts, idle allocation, staging, export/transport, external verification and review are not comprehensively timed; missing operational spans remain unknown. No full project bill or deleted-storage peak is claimed.

`analysis/` preserves approved frozen results. Reporting-only `analysis-reporting-v2/` relocates the historical 690-cell calibration count, corrects stale uncertainty prose and records completed canonical verification. Numeric invariance preserves 47288 original values, all frozen choices and byte-identical CSV; no metric/bootstrap/threshold was changed.

The small bundle contains summary/CSV, fresh proofs, invariance, scripts, original Source/input/core identities, inspected PNG and selected-run→accepted-receipt→catalog/part restoration mapping. Raw archives/tensors/inputs and canonical symlink targets are external dependencies; covering parts may overfetch unselected runs. Existing archive commitments are referenced, not a fresh complete binary rehash. Full replay requires exact own Source/raw restoration plus fresh safe byte/SHA/CRC and daily/latest/cost checks. The exporter’s symlink guard remains intact.

README-wide tests/lint were not rerun for this ignored artifact/reporting task. Fresh daily/latest/cost verification, numeric invariance, bundle integrity and inspected scientific plotting are the relevant checks. Artifact authoring used no fits, Final values, cloud, Git or ledger mutations; root subsequently published the verified bundle above. Root operational acceptance remains separate from peer scientific review.

## Artifact pins

| Artifact | SHA-256 |
|---|---|
|`study/matrix.json`|`ad4030302528b455b5ec6a90bae96492181232ea10d753d3c5d5d64de65ec7b5`|
|`independent-daily.json`|`ffa6c0ce202033939773d34edf9ce04c2f3364e22208ad1dd6928fbc156cad09`|
|`independent-states.json`|`91789626d6551a3bac338a73f5d87790c89bcf23843fe74e4e98464def56d19e`|
|`cost-integrity-v1.json`|`a1b88d58d6475f9278c1e9fbc3eb1a5805081fa842e1570126590efe78b3d2eb`|
|`analysis/summary.json`|`b4ea7adbf3caeadfb1c717da1e43d9b489661947d6d9da62a2930435dff839f8`|
|`analysis-reporting-v2/summary.json`|`fafdefd7fa2b93a0f052bc84eee05e1d2b2f56012d4b07eb7614bef0650aa922`|
|`analysis-reporting-v2/reporting-invariance.json`|`8749361461048eba1b216cef2343d4c480b0afd5e5f2080525f0f723408aee07`|
|`analysis-reporting-v2/runs.csv`|`ef067403b3f397e44fdf102fa29ff85d4164a0c86ff5039afb52065e596b4910`|
|`analysis-reporting-v2/ams-descriptive-v2.png`|`f5719931819f4e172cbeda3841df36aa52fa94cf4594aee37927a5bbad62496e`|
