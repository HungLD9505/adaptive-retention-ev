# MEL Development: complete canonical replication

[Published analysis/evidence bundle](https://drive.google.com/file/d/1b6b2A3wSTR3JHF8petObLOxHMbYFNRkv/view), 870,325 bytes, SHA `eaaa1b8d933d98c7fdc6646443bec9e7f0a4b39f621ff8cc827364c5c5d78653`. Root fresh native byte/SHA/ZIP-CRC and all 34 manifest-file checks passed. Raw dependencies remain external as specified below.

Issue #23; own Qyroven artifacts, reviewed 2026-10-27. All 27 declared station/history-budget/seed units and 378 method cells are externally accepted by the root coordinator. The new canonical view passed fresh CPU daily/latest-state and saved-cost checks. This is a descriptive Development handoff, without a superiority, population-effectiveness, independent peer-approval or Final-readiness claim.

## Scope and provenance

Root: `runs/issue23-mel-development-canonical-27-20261027-v1`. Exact ledger 44 SHA `a2c10c334badd75cae923aebf4adb42120de7a31ced1c95cd134a2513215d7db` selects retained or explicitly migrated accepted invocations by receipt/catalog/proof/report identities, never outcomes. The collection uses the declared new MEL replication and its own retained Sources; the old cached 59 targets are not mixed or adopted. Replacements are additional declared invocations, not recovery of original missing producer bytes. Old outputs remain preserved.

Each whole unit contains all 14 methods with predeclared method-specific configurations, matched input/runtime and exact shared issued/scored origins. The unchanged task is 24→24, history budgets 7/14/28 days, seeds 42/43/44 and 90 replay days. Cohort selection uses prefix count-rank bins and hashed identity within the ready Development population, not replay errors. There is no empty-prefix target in this cohort.

| Budget | Selected station IDs | Initial examples per station | Scored stations |
|---|---|---:|---:|
|7 days|15, 35, 53|6|3|
|14 days|60, 38, 9|13|3|
|28 days|16, 27, 32|27|3|

Selected populations differ by budget; aggregate differences are not a controlled history-budget effect. Publisher-local-naive clocks and deployment `2023-07-01T00:00:00` remain unchanged; publisher preprocessing/imputation and true availability-clock limitations remain. Raw archives were not freshly downloaded or rechecked by this report task.

Frozen primary SHA `ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6` fixes Source epochs 10, controller recipe 1, Fixed lambda 1.0, and proxy recipes Source error 1, uncertainty 1, drift 3 and parameter retention 2. `without_confidence` remains an alias for `online_best`. No city tuning, method/loss/controller/retention change or Hung implementation adoption was introduced.

The three own-city Sources were bound to the published Source-kit archive bytes including full reports and costs, then CPU-loaded for model/optimizer, city/dataset/stage/population, seed/10-epoch metadata, original report consistency and finite nonnegative 64-dimensional latent scales. Non-null target latent fingerprints match the corresponding Source. Producer Source environment is preserved independently of target environment.

| Seed | Own MEL replication Source SHA-256 |
|---|---|
|42|`5eb1778e3a9df10699fd614cffb8b37d667e541db6608d3d417054c2c9770c4c`|
|43|`11782c2f2cb773ec5c98745520f9e98dc899b510dd60fabf3bd2f25b2ba12bb0`|
|44|`f0be6ac27d6d635ad4bb869ef6f32551985d8ea4a10c664ff637b6dbe9844de1`|

Target environment counts: 182 cells: NVIDIA A100-SXM4-40GB, PyTorch 2.11.0+cu130; 28 cells: Tesla T4, PyTorch 2.11.0+cu128; 168 cells: Tesla T4, PyTorch 2.11.0+cu130. Within every unit all methods share the recorded environment, while different units can differ. All identified method/core file hashes agree despite producer Git-envelope differences: `aa9f91cdc828e0d48c693a26b306208ec41de640` (28 cells), `b85c15165c810a2be5332f030d739c0c59971cce` (350 cells). Analysis records clean commit `6483c64f6939ad4374a379a01a624950a77add78`. Mixed hardware, background work and different units prevent controlled speed comparisons.

## Verification and observed errors

Fresh daily verification covers 378 runs, 69,930 hashed files and 3,999 audit forecast scores. All 378 latest states passed. Report/state/event reconciliation passes 72,900 candidate steps, 3,999 audit steps and 972 initial adaptation steps. No training, inference or timer remeasurement was performed.

All 378 cells have 90 scored days and zero null metrics:34,020 scheduled, issued and scored method-days. Repeated method-day counts are not independent observations. Actual origins agree across methods and paired seeds; analysis does not fill missing labels or select favorable common days. Days are averaged within period, paired seeds within station, then stations receive equal weight.

| Budget | Adaptive MAE | Target-only MAE | Fixed retention MAE | Adaptive minus Fixed | Exploratory 95% paired interval |
|---|---:|---:|---:|---:|---|
|7 days|18.9005|33.7146|19.0492|-0.1487|[-2.1072, +1.6788]|
|14 days|24.4968|46.5335|26.7359|-2.2390|[-10.4382, +1.8136]|
|28 days|10.3758|17.4599|10.4397|-0.0640|[-0.3831, +0.1595]|

All errors are kWh. Positive gaps mean Adaptive has higher observed MAE. These are selected-cohort observations; a crossing-zero interval does not prove equivalence, and exploratory intervals do not establish population superiority. Adaptive station-level negative-transfer counts against Target-only are 0/3 (7 days), 0/3 (14 days), 0/3 (28 days). All 14 observed method means follow, including Seasonal naive; no favorable comparator subset is used.

| Method |7-day MAE|14-day MAE|28-day MAE|
|---|---:|---:|---:|
|adaptive|18.9005|24.4968|10.3758|
|block 28|19.0569|25.2969|10.2999|
|block 7|18.7528|25.0434|10.5319|
|drift|18.7841|23.6924|10.3612|
|fixed_retention|19.0492|26.7359|10.4397|
|frozen_source|18.4513|23.4270|15.4662|
|full_finetuning|19.5764|24.0407|11.5433|
|online_best|18.8406|25.0285|10.6165|
|parameter_retention|19.5846|24.0398|11.5409|
|seasonal_naive|28.8800|43.9547|12.6024|
|source_error|18.9097|24.6987|10.6495|
|target_only|33.7146|46.5335|17.4599|
|uncertainty|19.0503|25.9005|10.3055|
|without_source_initialization|33.5290|46.5434|17.9870|

Adaptive-minus-Target-only intervals for 7/14/28 days are [-39.7844, -0.5212], [-58.0099, -1.3841], [-18.8585, -1.7731]. Frozen bootstrap settings:2,000 draws,7-day circular calendar blocks, alpha 0.05 and seed 20261026; sampled stations share calendar draws, paired seeds are averaged conditionally. Undefined replicates: 0. Three nonrandom/possibly colocated stations per budget, calendar seams/nonstationarity, Development calibration and no simultaneous-comparison correction preclude population-confidence or calibrated predictive-coverage claims. No subgroup intervals are estimated.

The summary retains weekday/weekend, days 1–30/31–60/61–90, prefix load-density and initialization strata. Proxy relationships are same-block signal/error associations, not next-block predictions or causal retention benefits. Switching retains decision opportunities, missing outcomes and drain-only boundaries. There are 296 finalized isolated audit summaries, with 0 null paired gaps; neither harmful-switch rate nor recovery time is inferred. Definitions remain in `docs/reports/issue23-analysis-extensions.md`.

## Cost scope and reporting revision

Selected target process spans sum to 2800.964813 seconds. Three own Source ten-epoch trajectories total 24.089991 seconds and 1,440 optimizer steps, counted once across reuse. Canonical matrix wall time is null: this assembly is not one invocation. Component timers are subsets, never additive extra cost. Source time includes latent-scale/checkpoint work; target spans include Source/ensemble loading, adaptation, replay and serialization.

Inference/update counters include all active candidate branches; initial adaptation is performed once before cloning. Audit inference/update seconds and optimizer steps are separate. Per-lambda seconds/VRAM, audit clone/serialization-only overhead and incremental audit VRAM are not separately attributed; memory peaks are process peaks. Mixed hardware prevents controlled benchmarks. Tuning, retries, lost attempts, idle allocation, staging, export/transport, external verification and review are not comprehensively timed; missing operational spans remain unknown. No full project bill or deleted-storage peak is claimed.

`analysis/` preserves approved frozen results. Reporting-only `analysis-reporting-v2/` relocates the historical 690-cell calibration count, corrects stale uncertainty prose and records completed canonical verification. Numeric invariance preserves 47320 original values, all frozen choices and byte-identical CSV; no metric/bootstrap/threshold was changed.

The small bundle contains summary/CSV, fresh proofs, invariance, scripts, original Source/input/core identities, inspected PNG and selected-run→accepted-receipt→catalog/part restoration mapping. Raw archives/tensors/inputs and canonical symlink targets are external dependencies; covering parts may overfetch unselected runs. Existing archive commitments are referenced, not a fresh complete binary rehash. Full replay requires exact own Source/raw restoration plus fresh safe byte/SHA/CRC and daily/latest/cost checks. The exporter’s symlink guard remains intact.

README-wide tests/lint were not rerun for this ignored artifact/reporting task. Fresh daily/latest/cost verification, numeric invariance, bundle integrity and inspected scientific plotting are the relevant checks. Artifact authoring used no fits, Final values, cloud, Git or ledger mutations; root subsequently published the verified bundle above. Root operational acceptance remains separate from peer scientific review.

## Artifact pins

| Artifact | SHA-256 |
|---|---|
|`study/matrix.json`|`ae9021c1600d9edcfb09b4e937bb1331e91ad5dc9744f5a5faf8620c3650c915`|
|`independent-daily.json`|`3bc3aeb05f103269eb073c03d8d07841673536bcd8d8eaae25e842fe7867680e`|
|`independent-states.json`|`12ab769ee29911fbcacd8741e00af26e3a665c0adf8e327649ea3ed63fe56336`|
|`cost-integrity-v1.json`|`530611bc9db573a52320f211251dccc5f385b406fa964e19c5a45186148abe20`|
|`analysis/summary.json`|`e3c604290a57d9efa1136662971e0777ebec3044c2b4fb9f23efefd323ea9c16`|
|`analysis-reporting-v2/summary.json`|`fd8f58bc86b7d030766caf03c6c7a86098fdb60075dfcf424799047a474151f4`|
|`analysis-reporting-v2/reporting-invariance.json`|`85b3b58fef4a93de782eca776234b18bfb6a009d600935f6bce8d8857df16024`|
|`analysis-reporting-v2/runs.csv`|`c043065b92e4d1ee75f500071c2a1c9460d76546ffdca6ecb01f3ca4723ba433`|
|`analysis-reporting-v2/mel-descriptive-v1.png`|`9514147a420fa5068a9abeade1b8c6c34d745b6a264fd7564ca98ae72553ed34`|
