# SZH Development: complete canonical comparison

[Published analysis/evidence bundle](https://drive.google.com/file/d/1ju4vs0sGj52kGqzbl_fzzjCIX7X-bYDg/view), 992,587 bytes, SHA `a33579575bbf2489f7ccd13e324e31fa51194797d2661127611a3dbfa7a4e64a`. Root fresh native byte/SHA/ZIP-CRC and all 32 manifest-file checks passed. Raw dependencies remain external as specified below.

The accepted SZH collection contains 27 site/history-budget/seed units and 378 method cells. Fresh canonical daily, latest-state and saved-cost checks passed. All cells have 90 scored days. Adaptive has lower observed equal-site mean MAE than Target-only at each budget; Seasonal naive also has lower observed mean MAE than Adaptive at each budget. The exploratory Adaptive-minus-Fixed retention intervals all span zero. These observations do not establish population superiority or equivalence.

SZH is retained as a later-period Shenzhen supplement. The project documents extensive coordinate overlap with UrbanEV; physical-location independence is not established. This collection is not independent unseen-geography evidence, and it is not pooled with UrbanEV or another CHARGED city. See `docs/MASTER_RESEARCH_FLOW.md` and `docs/reports/charged-suitability.md`.

## Scope and provenance

Exact ledger48 SHA `4a606c5265036468d4d7a8c5c3d089b70c5ecb1f0c5fe5d0c28c5904ec47dae8` selects accepted retained or explicitly migrated invocations by receipt/catalog/proof/report identity, without outcome-based selection. The canonical inventory SHA is `de51fa087900e97d10d46990c37e450681afe8d28b98f594e5d74a725435ce96`. Old outputs are preserved. Migration results are additional declared invocations rather than recovery of missing original producer bytes.

The task remains 24→24 with 7/14/28-day histories, seeds 42/43/44 and 90 replay days. Each unit contains all 14 predeclared variants, matched input/runtime and common actual issued/scored origins. CHARGED entities here are publisher virtual sites (charger clusters); the analysis field named `station_first` gives these sites equal weight. Cohort selection uses prefix-count ranks and hashed identity in ready Development populations.

| History | Selected site IDs | Initial examples per site | Ready Development sites | Scored selected sites |
|---|---|---|---:|---:|
|7 days|4, 242, 119|6, 6, 6|288|3|
|14 days|473, 655, 793|13, 13, 13|288|3|
|28 days|86, 613, 14|27, 27, 27|288|3|

Different budgets select different sites and demand scales. Aggregate differences across budgets do not identify a causal history-budget effect. The cohort has no empty-prefix entity. Publisher-local-naive clocks and deployment `2023-07-01T00:00:00` are unchanged. Publisher imputation/preprocessing and unknown true availability clocks limit strict-online interpretation. This task did not freshly acquire or verify raw dataset archives.

Frozen primary SHA `ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6` fixes Source epochs 10, controller recipe 1, Fixed retention lambda 1.0, and proxy recipes Source error 1, uncertainty 1, drift 3 and parameter retention 2. `without_confidence` remains an alias for `online_best`. No city-specific tuning, changed method/loss/controller/retention, pooled pretraining or Hung implementation adoption is introduced.

## Original Sources and recorded environments

The three own-SZH Source trajectories were checked against the published archive bytes, including full reports, costs and logs, then CPU-loaded. Dataset/city/stage/population, seed, ten-epoch metadata, report/checkpoint identity and finite nonnegative 64-dimensional latent scales agree. Every non-null target latent fingerprint matches its corresponding original Source.

| Seed | Original Source checkpoint SHA-256 |
|---|---|
|42|`c8da9be3701c65c3cf96edd5f979ff2457beaeaba7611459568d7b3e0e53352a`|
|43|`6b3fde03bf169d81d252a62d3cd15323493e165a9fa92bbaa869a369d7efffee`|
|44|`6b7c8aec3f7f017628f298f766a53d49d16c1f6de174a7a897d080d7db5c0c4b`|

Target profiles: 196 cells on NVIDIA A100-SXM4-40GB with PyTorch 2.11.0+cu130; 182 cells on Tesla T4 with PyTorch 2.11.0+cu130. Every unit has a common recorded environment across methods. Cross-unit hardware variation prevents a controlled hardware-speed comparison or numerical-equivalence claim. Original Source environments remain separate from target environments.

Target code commits: `b85c15165c810a2be5332f030d739c0c59971cce` (378 cells). Core file identities match the original predeclared context. Frozen analysis records clean commit `46258bfa1ea045efd1e923b601ed6a9318f3908a`.

## Fresh verification and descriptive results

Fresh daily checks cover 378 runs and 69,930 hashed files; all 378 latest states passed. Cost/state/event reconstruction reconciles 72,900 candidate, 4,314 audit and 972 initial adaptation optimizer steps. These checks use saved outputs and CPU integrity loads; no fitting, inference or timer remeasurement was performed.

The 34,020 scheduled, issued and scored method-days contain no null metric cells. Repeated method-days are not independent observations. The canonical resolver checked actual common origins, without filling missing labels or selecting favorable days. The approved estimator averages days within period, fixed paired seeds within site, then assigns equal weight to sites.

| History | Adaptive MAE | Target-only MAE | Fixed retention MAE | Seasonal naive MAE | Adaptive minus Fixed | Exploratory 95% interval |
|---|---:|---:|---:|---:|---:|---|
|7 days|5.9664|6.6021|5.8493|5.9521|+0.1171|[-0.0579, +0.5192]|
|14 days|3.3697|10.5463|3.3882|2.0246|-0.0185|[-0.3668, +0.2766]|
|28 days|57.2144|83.7780|57.2206|53.4059|-0.0063|[-3.7046, +3.5790]|

Errors are kWh. Positive differences mean Adaptive has higher observed MAE. The intervals describe conditional, selected-cohort resampling; spanning zero proves neither equivalence nor absence of an effect. Adaptive negative-transfer site counts against Target-only are 0/3 at 7 days, 0/3 at 14 days, 0/3 at 28 days. All seeds and all 14 methods remain in the report.

| Method | 7-day MAE | 14-day MAE | 28-day MAE |
|---|---:|---:|---:|
|adaptive|5.9664|3.3697|57.2144|
|block28|5.9477|3.3501|57.3639|
|block7|5.9802|3.3192|58.2517|
|drift|5.9842|3.3155|58.7737|
|fixed_retention|5.8493|3.3882|57.2206|
|frozen_source|7.2574|2.1465|63.3921|
|full_finetuning|5.9408|3.5377|61.4799|
|online_best|5.9123|3.3581|57.5066|
|parameter_retention|5.9409|3.5329|61.4516|
|seasonal_naive|5.9521|2.0246|53.4059|
|source_error|5.9636|3.3101|57.6127|
|target_only|6.6021|10.5463|83.7780|
|uncertainty|5.9636|3.3185|57.2925|
|without_source_initialization|6.5666|10.5665|85.4675|

The frozen exploratory bootstrap uses 2,000 draws, 7-day circular calendar blocks, alpha 0.05 and seed 20261026. Shared calendar draws retain paired methods; seeds are averaged conditionally. Undefined interval replicates total 0. Three nonrandom/possibly colocated sites per budget, circular seams/nonstationarity, Development calibration and no simultaneous-comparison correction preclude population-confidence or calibrated predictive-coverage claims. No subgroup intervals are estimated.

The summaries retain weekday/weekend, days 1–30/31–60/61–90, prefix load-density and initialization strata. Proxy relationships are same-block signal/error associations, not next-block predictions or causal retention benefits. Switching summaries retain decision opportunities, missing outcomes and drain-only boundaries. There are 324 finalized isolated audit summaries, including 0 null paired gaps. Harmful-switch rates and recovery times are not inferred. Definitions remain in `docs/reports/issue23-analysis-extensions.md`.

## Cost scope and unchanged reporting values

Selected target process spans sum to 2888.459394 seconds. Three own-SZH Source ten-epoch spans total 585.589382 seconds and 37,380 training optimizer steps, counted once across reuse. Canonical wall time is null because assembly is not a single original invocation. Component timers are subsets of process spans, never additional totals.

Target counters include active candidate branches; initial adaptation happens once before cloning. Audit counters and optimizer steps are separate. Per-lambda seconds/VRAM, audit clone/serialization overhead and incremental audit VRAM are not separately attributed; memory peaks are process peaks. Tuning, retries, lost work, idle allocation, staging, export/transport, external verification and review are not comprehensively timed. No full project bill, deleted-storage peak, controlled hardware benchmark or unrecorded overhead is invented.

`analysis/` preserves the approved frozen outputs. Reporting-only `analysis-reporting-v2/` relocates the historical 690-cell calibration count, clarifies stale uncertainty prose and records completed canonical verification. Invariance checks preserve 47032 original numeric values, all frozen choices and byte-identical `runs.csv`. SZH temporal/overlap limits are explicit; no metric, bootstrap setting or threshold changed.

## Portable evidence and remaining review

The inspected PNG shows every method and all three budget-specific Adaptive-minus-Fixed intervals. The selected restore map binds each run to its accepted receipt and covering catalog part, with overfetch explicit. The analysis bundle contains summaries, CSV, fresh proofs, invariance, source/input/core identities, scripts and this draft. Raw archives, checkpoints, inputs and symlink targets remain external dependencies; the bundle is an inspection handoff rather than a self-contained replay package. Restore exact raw parts and original Sources with safe byte/SHA/CRC checks, then rerun fresh daily/latest/cost verification. The exporter symlink guard remains intact.

README-wide tests/lint were not rerun for this ignored artifact workflow. Fresh daily/latest/cost checks, frozen-analysis authentication, numeric/CSV invariance, bundle integrity and visual PNG inspection cover this handoff. Root operational acceptance remains separate from peer scientific and capacity review. No fits, Final execution/values, cloud publication, Git changes or ledger mutations were performed by this SZH CPU workflow.

## Artifact pins

| Artifact | SHA-256 |
|---|---|
|`study/matrix.json`|`73ad61e746cf82d2e2481809f3114ef7781a2aef8bf6ea3dbdda3492de823980`|
|`inventory.json`|`de51fa087900e97d10d46990c37e450681afe8d28b98f594e5d74a725435ce96`|
|`independent-daily.json`|`ce7a171782a9c21a1c8b22cad823c03335b40c25ed99ceb9af8acf00fd48ff32`|
|`independent-states.json`|`677b0a9bb139eccc01c830819d6a51c65bdfba3e56b513a82895d06304be1d7b`|
|`cost-integrity-v1.json`|`6c3c0babcc142577af1ed86cfe7e0384b96a362918ff0bd2f11fe34e588a8878`|
|`analysis/summary.json`|`a14ae46f66e29459c22dbf2917c3fd14a1b5e50aea4445e847def489227561d7`|
|`analysis-reporting-v2/summary.json`|`96540b4119020d0c4735643e215c957a7639581c2f893eb463870b52b073aa70`|
|`analysis-reporting-v2/runs.csv`|`1d58ed312db1a8f85432623ba55933298690438586a63cb51a02c01e0b73c67b`|
|`analysis-reporting-v2/reporting-invariance.json`|`f6b71d86c2c2179f3695e6bd4da57ff4df3e561eeaeac0566f3dc6cd0e9d938e`|
|`analysis-reporting-v2/szh-descriptive-v2.png`|`d67ffbc584dcca7b9b6a13b0d22351dc39f4002a22a39d266b6ac3ff181757e8`|
