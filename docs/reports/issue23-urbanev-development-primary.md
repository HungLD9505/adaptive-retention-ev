# UrbanEV Development: complete canonical primary collection

Issue #23; own Qyroven artifacts, recorded 2026-10-27. The canonical UrbanEV
Development collection now contains all 69 declared station/budget/seed units and
966 method cells. Whole units have external artifact acceptance; this report and
its analysis remain subject to independent technical/scientific review. No Hung
implementation adoption, population superiority, novelty, Final result or Final
configuration/analysis lock is claimed. CHARGED cities remain separate scopes.

## Collection and verification

Run root: `runs/issue23-primary-canonical-69-20261027-v1`. Each complete unit
contains all 14 methods on one dataset/city/station/history-budget/seed identity.
The predeclared budgets are 7/14/28 days and paired seeds are 42/43/44. Replay
retains the unchanged 24→24 task and 90-day deployment calendar.

Canonical replacement follows the accepted whole-unit ledger and input/config
identities, not outcomes. It retains 16 original accepted units, 28 Kaggle units
and 25 Colab units. Each unit has identical input and execution-environment
bindings across all 14 methods. Original and migrated environments differ across
units: the recorded T4 runtimes include PyTorch 2.11.0 with CUDA 12.8 and 13.0
builds. Platform, source/model/controller random seeds and nonrandom cohort
membership therefore cannot be isolated as causal factors.

Fresh canonical daily verification covers 966 runs and 178,710 hashed files. It
binds saved forecasts, candidate/deployed errors, availability, commit chains,
decision events and isolated audit scores to identified Development inputs. Fresh
latest-state verification CPU-loaded and content-rehashed 966 latest target
states. It does not reconstruct omitted historical states or independently
repeat training. The canonical run tree is a local symlink view, not a portable
export archive. No raw archive was freshly downloaded or rechecked for this
analysis; historical raw fingerprints are not fresh-download evidence.

The original three UrbanEV Source checkpoints remain unchanged, produced at
`ff42ea944bf05b4b77e2b730edf500b1fee6e851` for 10 epochs. Every target identifies
the Source checkpoint for its own comparison seed. Core algorithm file hashes
match across accepted runs and analysis despite differing recorded Git commits;
analysis code identity is `a8d1de7796cdbba549cbcc24be11ec5feb83cab5`. Source
producer metadata is retained; migration does not relabel it as target runtime
metadata. Full per-run lineage and Source identities accompany the small bundle.

| Source seed | Original checkpoint SHA-256 |
|---|---|
| 42 | `a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b` |
| 43 | `2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f` |
| 44 | `6f475e54768322c5b51f5837d6ce7e863cb9ef6d33aec05b4a1c2468cd0285a5` |

## Frozen choices and coverage

Choices remain bound to historical primary analysis SHA-256
`ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6`:
Source epochs 10; controller recipe 1; Fixed retention lambda 1.0; proxy recipes
Source error 1, uncertainty 1, drift 3 and parameter retention 2. The
`without_confidence` alias remains `online_best`; the block7 comparator remains
`adaptive`. These are conditional Development selections, not held-out evidence.

The 14 executed method names are `adaptive`, `block28`, `block7`, `drift`,
`fixed_retention`, `frozen_source`, `full_finetuning`, `online_best`,
`parameter_retention`, `seasonal_naive`, `source_error`, `target_only`,
`uncertainty` and `without_source_initialization`. No required null method cell
was removed. Reporting revision `analysis-v2` relocates the historical 690-cell
calibration count into provenance, keeping the actual canonical count 966.

Across all method cells there are 86,940 scheduled, 58,044 issued and 32,508
scored days. There are 462 null cells: 11 unscored station/budget combinations ×
three seeds × 14 methods. Null means unscorable, not zero error. Different budget
populations prevent a controlled history-budget-effect interpretation.

| History budget | Declared stations | Scored stations | Unscored station IDs |
|---|---:|---:|---|
| 7 days | 6 | 3 | 1050, 1200, 2447 |
| 14 days | 8 | 4 | 1987, 2644, 2613, 1025 |
| 28 days | 9 | 5 | 1987, 1188, 1408, 1251 |

## Descriptive findings and uncertainty

Metrics require identical actual issued/scored origins across methods within each
unit and identical scored origins across paired seeds. First average seeds within
station, then give each scored station equal weight. All full 24-hour labels must
be available for a scored forecast; gaps are retained. Period RMSE takes the root
after averaging daily MSE; macro RMSE averages station/seed period RMSE.

| Budget | Adaptive MAE | Target-only MAE | Fixed retention MAE | Adaptive minus Fixed | Exploratory 95% paired interval |
|---|---:|---:|---:|---:|---|
| 7 days | 4.8420 | 8.7750 | 4.8081 | +0.0339 | [-0.1179, +0.1737] |
| 14 days | 5.0988 | 8.0235 | 5.0570 | +0.0418 | [-0.0754, +0.1756] |
| 28 days | 5.5244 | 8.5289 | 5.4998 | +0.0246 | [-0.0835, +0.1453] |

All errors and gaps above are kWh. Adaptive has lower observed MAE than
Target-only and slightly higher observed MAE than selected Fixed retention in
these scored populations. Its station-level negative-transfer rate relative to
Target-only is zero in the 3/4/5 scored stations, not in all declared stations or
the dataset population. Adaptive-minus-Target-only exploratory intervals are
[-7.5860, -1.4899], [-4.2107, -1.7010] and [-4.4233, -1.8167] for 7/14/28 days.
These observations do not establish method superiority or equivalence.

The fixed analysis profile uses 2,000 resamples, common 7-day circular calendar
blocks across sampled stations, alpha 0.05 and seed 20261026. The three paired
comparison seeds are averaged conditionally, not sampled as independent stations.
No bootstrap replicate is undefined in these reported comparisons. Small,
nonrandom/possibly colocated cohorts, calendar seams/nonstationarity and no
simultaneous-comparison correction limit interpretation. These are exploratory
marginal intervals, not population confidence guarantees or calibrated predictive
coverage. Subgroup intervals are not estimated; no Final analysis lock is granted.

Weekday/weekend, fixed days 1–30/31–60/61–90, prefix-derived load-density and
initialization strata remain separate descriptive outputs. Proxy associations
pair available signals with candidate differences from the same decision-used
block; they do not establish next-block prediction or causal retention benefits.
Switch paths retain scheduled opportunities, missing outcomes and drain-only
boundaries. The summary retains 344 finalized isolated audit summaries, 44 with
null gaps, without inventing a harmful-switch threshold or recovery time. See the
[analysis definitions and timer boundaries](issue23-analysis-extensions.md).

## Cost and reporting revision

The three selected Source fits have recorded elapsed time 446.0584 seconds,
charged once across reused comparisons. This is not total calibration cost or a
standalone Source cost charged to every method. Historical calibration family
wall times are Source 1,185.8365, Fixed 949.9659, proxy 6,894.1140 and matched
3,053.8848 seconds; controller wall time is unknown. Their known sum 12,083.8012
seconds is incomplete and overlaps selected Source/target views. Do not add it to
canonical row costs or label it an end-to-end total.

Source elapsed already includes record loading on a cache miss, model/optimizer
setup, training, per-epoch latent-scale estimation and checkpoint writes/reload.
Target elapsed includes Source/ensemble loading, adaptation, replay and daily
serialization; tagged component timers are subsets. Caller-side shared input
preparation, final report work after the timer, packaging, transfer and external
verification lack comprehensive end-to-end accounting. The summary's broad
preparation-cost shorthand does not imply that measured latent-scale or ensemble
loading must be added again. Platform/cache/background-work differences prevent
controlled throughput conclusions from mixed-runtime sums.

`analysis-v2` changes reporting metadata only: it clarifies historical count and
uncertainty prose, and separates incomplete cost scopes. Exact comparison checked
93,579 existing numeric values unchanged, preserved frozen decision values and
left `runs.csv` byte-identical. No metric, bootstrap choice/result, model,
controller, cohort, input or forecast changed. Original `analysis/` is preserved.

## Artifacts and verification scope

The local bundle is
`runs/issue23-primary-canonical-69-20261027-v1/urbanev-development-primary69-analysis-v1.zip`
(503,773 bytes). It includes summary, run CSV, invariance proof, lineage,
provenance, manifest, plotting source and a visually inspected PNG. Every member
fingerprint and ZIP CRC passed. It excludes symlink targets, checkpoints, raw
labels and large daily/state evidence; it supports standalone result inspection,
not complete replay or renewed independent acceptance. It has not been published
or checked by a teammate through this report task.

| Artifact | SHA-256 |
|---|---|
| Canonical matrix | `0d0a755cae6aebce0dfb8d9f331d31c3752e1fa159d911eded9d21acb46e3a8d` |
| Fresh daily proof | `092ad49a16b634049e6e9b81b8547e6d37c01767f28f2b2f013b0055019138b8` |
| Latest-state proof | `66a3ce95c19c99d642ba304c3de7f0a833cf43f91f3475f642870998d474d4df` |
| Analysis-v2 summary | `c3d9499be9af224c982cb7079610665b5754745f7763c95999c1d7127ca27dc2` |
| Reporting invariance | `08714a5b96abf1a83dceb20d83e61454b7030c3af4057a7f28a6fde4a61f502b` |
| Run CSV | `16601ab8ee312cf74b997374fb2f2bb7b2704bd49efa784728beb1ca7ddc4fc7` |
| Small bundle | `f1adbeb00892cc17b4b6fdbbb818d425e7e2dee340a64d2bd2792aaa85dfc0ba` |
| Bundle manifest | `910205e8d926d97225f65f3f4a6e86f3b1b090cc7eb99d832b76399b6fd6819a` |
| Descriptive PNG | `145150b62a2c23b6b78722db1a4bb52bcb57c901fb3698a3179333ada277cb6a` |

This documentation/bundle task used stored summaries and provenance only. It ran
no training, raw-data download, fresh daily/state re-verification, Final-value
access, cloud publication or Git/ledger mutation. Fixture tests and README-wide
code checks were not rerun for this documentation/plot-only change. Numeric
invariance, bundle member hashes/CRC and visual inspection passed; they do not
replace peer review, scientific validity assessment or the separate Final gate.
