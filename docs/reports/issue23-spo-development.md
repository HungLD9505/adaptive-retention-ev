# SPO Development: complete canonical comparison

[Published analysis/evidence bundle](https://drive.google.com/file/d/1jBT5_WMQ4c-O1y8rklgv5KEDjnXbwtBh/view), 879,378 bytes, SHA `feaa459ad58c9656363eb4a262de6ba4633c65083629799a4525899ef538d3a2`. Root fresh native byte/SHA/ZIP-CRC and all 37 manifest-file checks passed. Raw dependencies remain external as specified below.

Issue #23; own Qyroven artifacts, reviewed 2026-10-27. All 27 declared station/history-budget/seed units and 378 method cells are externally accepted by the root coordinator. The new canonical view passed fresh CPU daily/latest-state and saved-cost checks. This is a descriptive Development handoff, without a superiority, population-effectiveness, independent peer-approval or Final-readiness claim.

## Scope and provenance

Root: `runs/issue23-spo-development-canonical-27-20261027-v1`. Exact ledger 47 SHA `2a4b5fadaf2403d5cae8637765a5a961fad3d017c5e1253f3460a7304817ca86` selects retained or explicitly migrated accepted invocations by receipt/catalog/proof/report identities, never outcomes. The collection uses its own retained original SPO Sources. Replacements are additional declared invocations, not recovery of original missing producer bytes. Old outputs remain preserved.

Each whole unit contains all 14 methods with predeclared method-specific configurations, matched input/runtime and exact shared issued/scored origins. The unchanged task is 24→24, history budgets 7/14/28 days, seeds 42/43/44 and 90 replay days. Cohort selection uses prefix count-rank bins and hashed identity within the ready Development population, not replay errors. There is no empty-prefix target in this cohort.

| Budget | Selected station IDs | Initial examples per station | Scored stations |
|---|---|---:|---:|
|7 days|17, 11, 41|6|3|
|14 days|26, 40, 11|13|3|
|28 days|18, 17, 39|27|3|

Selected populations differ by budget; aggregate differences are not a controlled history-budget effect. Publisher-local-naive clocks and deployment `2023-07-01T00:00:00` remain unchanged; publisher preprocessing/imputation and true availability-clock limitations remain. Raw archives were not freshly downloaded or rechecked by this report task.

Frozen primary SHA `ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6` fixes Source epochs 10, controller recipe 1, Fixed lambda 1.0, and proxy recipes Source error 1, uncertainty 1, drift 3 and parameter retention 2. `without_confidence` remains an alias for `online_best`. No city tuning, method/loss/controller/retention change or Hung implementation adoption was introduced.

The three own-city Sources were bound to the published Source-kit archive bytes including full reports and costs, then CPU-loaded for model/optimizer, city/dataset/stage/population, seed/10-epoch metadata, original report consistency and finite nonnegative 64-dimensional latent scales. Non-null target latent fingerprints match the corresponding Source. Producer Source environment is preserved independently of target environment.

| Seed | Original SPO Source SHA-256 |
|---|---|
|42|`6e096dd5c74582b725777c1b1af3009fd2fb9af7d5e140a05e6abbe61ebd7376`|
|43|`75f93b6b39d8223cba3ee6c95ab8509a3f4749359d645a6f3b5cf9ca1f19388f`|
|44|`18003c08b4741cc5c40228a5f2c40efb89aa9c4f4597759b6b1d1a4e83df5b0a`|

Target environment counts: 168 cells: NVIDIA A100-SXM4-40GB, PyTorch 2.11.0+cu130; 42 cells: Tesla T4, PyTorch 2.11.0+cu128; 168 cells: Tesla T4, PyTorch 2.11.0+cu130. Within every unit all methods share the recorded environment, while different units can differ. All identified method/core file hashes agree despite producer Git-envelope differences: `aa9f91cdc828e0d48c693a26b306208ec41de640` (42 cells), `b85c15165c810a2be5332f030d739c0c59971cce` (336 cells). Analysis records clean commit `46258bfa1ea045efd1e923b601ed6a9318f3908a`. Mixed hardware, background work and different units prevent controlled speed comparisons.

## Verification and observed errors

Fresh daily verification covers 378 runs, 69,930 hashed files and 4,655 audit forecast scores. All 378 latest states passed. Report/state/event reconciliation passes 72,900 candidate steps, 4,655 audit steps and 972 initial adaptation steps. No training, inference or timer remeasurement was performed.

All 378 cells have 90 scored days and zero null metrics:34,020 scheduled, issued and scored method-days. Repeated method-day counts are not independent observations. Actual origins agree across methods and paired seeds; analysis does not fill missing labels or select favorable common days. Days are averaged within period, paired seeds within station, then stations receive equal weight.

| Budget | Adaptive MAE | Target-only MAE | Fixed retention MAE | Adaptive minus Fixed | Exploratory 95% paired interval |
|---|---:|---:|---:|---:|---|
|7 days|1.9460|2.7389|1.9103|+0.0357|[-0.0707, +0.1445]|
|14 days|0.5679|0.8907|0.5307|+0.0372|[-0.0057, +0.1115]|
|28 days|0.6540|1.1912|0.6504|+0.0036|[-0.0445, +0.0811]|

All errors are kWh. Positive gaps mean Adaptive has higher observed MAE. These are selected-cohort observations; a crossing-zero interval does not prove equivalence, and exploratory intervals do not establish population superiority. Adaptive station-level negative-transfer counts against Target-only are 0/3 (7 days), 0/3 (14 days), 0/3 (28 days). All 14 observed method means follow, including Seasonal naive; no favorable comparator subset is used.

| Method |7-day MAE|14-day MAE|28-day MAE|
|---|---:|---:|---:|
|adaptive|1.9460|0.5679|0.6540|
|block 28|1.9518|0.5571|0.6556|
|block 7|1.9256|0.5591|0.6719|
|drift|1.9912|0.5761|0.6558|
|fixed_retention|1.9103|0.5307|0.6504|
|frozen_source|2.1645|0.5627|0.5727|
|full_finetuning|2.0523|0.5804|0.6575|
|online_best|1.9696|0.5598|0.6648|
|parameter_retention|2.0523|0.5804|0.6573|
|seasonal_naive|2.0396|0.8140|1.0192|
|source_error|1.9414|0.5510|0.6864|
|target_only|2.7389|0.8907|1.1912|
|uncertainty|1.9580|0.5576|0.6561|
|without_source_initialization|2.7939|0.8974|1.2318|

Adaptive-minus-Target-only intervals for 7/14/28 days are [-1.6590, -0.2231], [-0.7181, -0.1205], [-1.0565, -0.0190]. Frozen bootstrap settings:2,000 draws,7-day circular calendar blocks, alpha 0.05 and seed 20261026; sampled stations share calendar draws, paired seeds are averaged conditionally. Undefined replicates: 0. Three nonrandom/possibly colocated stations per budget, calendar seams/nonstationarity, Development calibration and no simultaneous-comparison correction preclude population-confidence or calibrated predictive-coverage claims. No subgroup intervals are estimated.

The summary retains weekday/weekend, days 1–30/31–60/61–90, prefix load-density and initialization strata. Proxy relationships are same-block signal/error associations, not next-block predictions or causal retention benefits. Switching retains decision opportunities, missing outcomes and drain-only boundaries. There are 347 finalized isolated audit summaries, with 0 null paired gaps; not every last-block audit is thereby guaranteed finalized, and neither harmful-switch rate nor recovery time is inferred. Definitions remain in `docs/reports/issue23-analysis-extensions.md`.

## Zero-error and coverage cases retained

All 378 target metrics are scored; zero error remains a numerical zero rather than a missing value or an automatic floor. Seasonal naive has 3 exact-zero MAE cells; all methods’ exact-zero counts and row identities remain in coverage-zero-error-review-v1.json. A zero-error observation is descriptive for these observed days, not proof of a forecasting mechanism or universal predictability. Target-only zero-baseline station counts by budget are 7: 0, 14: 0, 28: 0. Where a Target-only denominator is zero, proportional gain/negative-transfer status remains undefined and is omitted from the rate denominator, while absolute errors/gaps remain retained. No missing labels were filled as zero.

## Cost scope and reporting revision

Selected target process spans sum to 2823.812039 seconds. Three own Source ten-epoch trajectories total 16.545261 seconds and 1,230 optimizer steps, counted once across reuse. Canonical matrix wall time is null: this assembly is not one invocation. Component timers are subsets, never additive extra cost. Source time includes latent-scale/checkpoint work; target spans include Source/ensemble loading, adaptation, replay and serialization.

Inference/update counters include all active candidate branches; initial adaptation is performed once before cloning. Audit inference/update seconds and optimizer steps are separate. Per-lambda seconds/VRAM, audit clone/serialization-only overhead and incremental audit VRAM are not separately attributed; memory peaks are process peaks. Mixed hardware prevents controlled benchmarks. Tuning, retries, lost attempts, idle allocation, staging, export/transport, external verification and review are not comprehensively timed; missing operational spans remain unknown. No full project bill or deleted-storage peak is claimed.

`analysis/` preserves approved frozen results. Reporting-only `analysis-reporting-v2/` relocates the historical 690-cell calibration count, corrects stale uncertainty prose and records completed canonical verification. Numeric invariance preserves 47309 original values, all frozen choices and byte-identical CSV; no metric/bootstrap/threshold was changed.

The small bundle contains summary/CSV, fresh proofs, invariance, scripts, original Source/input/core identities, inspected PNG and selected-run→accepted-receipt→catalog/part restoration mapping. Raw archives/tensors/inputs and canonical symlink targets are external dependencies; covering parts may overfetch unselected runs. Existing archive commitments are referenced, not a fresh complete binary rehash. Full replay requires exact own Source/raw restoration plus fresh safe byte/SHA/CRC and daily/latest/cost checks. The exporter’s symlink guard remains intact.

README-wide tests/lint were not rerun for this ignored artifact/reporting task. Fresh daily/latest/cost verification, numeric invariance, bundle integrity and inspected scientific plotting are the relevant checks. Artifact authoring used no fits, Final values, cloud, Git or ledger mutations; root subsequently published the verified bundle above. Root operational acceptance remains separate from peer scientific review.

## Artifact pins

| Artifact | SHA-256 |
|---|---|
|`study/matrix.json`|`d1d7b29b5f7ae339c56702cbb242e11e125579710acd95d923655d63375c56a7`|
|`independent-daily.json`|`1e076d6d43eb9d7e956aea7a83739314941ae51fadf147714a4a9868a1c97327`|
|`independent-states.json`|`af99f0beac818698653bda43d1461d6edbc1398a9ac3058a96d37c46d4587c0b`|
|`cost-integrity-v1.json`|`8e122da810954e02972c8f06cb0c6b6d13079b7839aa621bee22b1e337922762`|
|`analysis/summary.json`|`34bc9cf9c06cf1b3b7fb3d09e484ba6b23509c182013bb26574e42370e87dc93`|
|`analysis-reporting-v2/summary.json`|`5f2dd2eb834e65431008a3ef19f0f37706aaf2f6f7207a84caee11416e7c0c47`|
|`analysis-reporting-v2/reporting-invariance.json`|`3d2a21bfdddb144c2c35ee21a6625eae04b793fde031504342b694fcdc3c1767`|
|`analysis-reporting-v2/runs.csv`|`ad9b24b81b48298ca6309bffaaa7fae2ce7d2672aec239c91d7a8ac9ee11e2a3`|
|`analysis-reporting-v2/spo-descriptive-v1.png`|`c7bda63ce493df662e08de3b835a597eeab5e2935e2f730aa791be8f4c1a413c`|
