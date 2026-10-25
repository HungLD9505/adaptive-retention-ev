# Comparable finite proxy and parameter-retention Development grids

Issue #23 / PR #52, independent Qyroven implementation. Pre-execution declaration;
no new schedule and no Final lock. Follow the completed, independently verified
controller calibration and recompute its provisional recipe from every candidate,
seed, station and budget cell. Reuse that common Source10 family and controller
candidate levels, initialization, confidence/block/update settings for proxy methods.
Do not silently inherit the earlier one-epoch diagnostic profiles.

Each method gets exactly four joint configurations and all 69 paired
entity-budget-seed units (three seeds, 7/14/28-day budgets, 90-day replay): 276 runs
per method, 1,104 total. Four configurations matches the Adaptive Controller search
count, but runtime differs and must be measured; equal count is not equal compute.
The finite budgets are deliberately explicit, not exhaustive optimizer searches.

| Method | Threshold pair A | Threshold pair B | Mapping choices |
|---|---|---|---|
| Source error | 0.1 / 0.5 | 0.05 / 0.25 | Ascending or descending retention |
| Uncertainty | 0.01 / 0.05 | 0.005 / 0.025 | Ascending or descending retention |
| Drift | 0.5 / 1.5 | 1 / 3 | Ascending or descending retention |

Recipe order is A ascending, A descending, B ascending, B descending. Source error
and uncertainty are on fixed target-normalized energy scale; drift is RMS of
prefix-standardized history descriptors, hence dimensionless. Thresholds represent
bounded alternatives around the declared diagnostic values, not values estimated
using future/Final observations. Only the causal block-mean available signals enter
the selectors. High signal is not assumed to imply low retention. The fixed
three-member Source ensemble uses all identified seeds 42/43/44 at the common
Source duration, with all preparation/inference costs recorded; seed dispersion
is not probabilistically calibrated predictive uncertainty. Bin occupancy and
proxy-versus-paired-retention-error relationships still require actual analysis.
Only two monotone orders are tested, not all permutations; unsupported estimator
or optimality claims are prohibited.

Parameter Retention gets its own four positive level pairs:
0.001/0.01, 0.01/0.1, 0.1/1 and 1/10, initial lambda the lower positive level and
lambda zero present in every candidate set. Keep selected confidence/block settings
and the existing encoder-only mean parameter penalty. These units differ from the
latent penalty, so this independent range is explicit; do not equate numerical
lambdas across definitions. Report an endpoint winner as a range limitation.

The Source and common controller are selected using Development only, in declared
stages. This is conditional selection, not a nested held-out performance estimate.
Station-first/equal-budget original-unit MAE chooses each method's recipe, with
exact ties resolved by recipe index. Retain every null cell and require complete
paired coverage and actual config-to-recipe bindings. No best-seed selection,
Final labels, local real-data training or automatic Final configuration approval.

`tools.proxy_calibration` authenticates profile/controller/cohort/Source identities,
requires the independent controller verifier, keeps original data and old outputs,
and uses a new CUDA directory. Model/optimizer/RNG isolation, forecast-before-label
order and independent audit branches are inherited unchanged from the runner.
Per-run GPU peaks reset after common preparation. Latest states and all daily
forecast/event commit chains, logs and costs are retained. Preserve failed runs;
partial batch resume orchestration remains manual with identified checkpoints.

## Completed Kaggle calibration — 2026-10-26

All **1,104/1,104** declared GPU replays completed at clean training commit
`54131cbb8ce47f9d064b80f03956e8e62ec48346`, on one visible Tesla T4,
PyTorch 2.11.0+cu128 / CUDA12.8 / Python3.13.15. The matrix records
6,894.114 seconds inside its replay loop; the enclosing CLI log records
6,903.310 seconds including startup. These are different timer boundaries.

The Kaggle verifier authenticated **204,240 daily files**, preserving 528 null
metric cells and 100,464 explicitly omitted historical checkpoint states.
Downloaded complete matrix/proof pairs pass local population, chain, original-unit
metric and exact finite-selection authentication. All configurations, paired
seeds 42/43/44 and the declared cohort remain present. Full daily-file bytes and
all latest states have **not yet been restored independently off-runtime**.
A metadata/proof package is not a complete checkpoint or runtime backup.

Conditional Development MAE in kWh; first average paired seeds within station,
then stations within budget, then the three budget means with equal weight:

| Method | Recipe | 7-day | 14-day | 28-day | Equal-budget score |
|---|---|---:|---:|---:|---:|
| `source_error` | 0 | 4.846813 | 5.122739 | 5.526969 | 5.165507 |
| `source_error` | 1 (selected) | 4.846813 | 5.097881 | 5.526969 | 5.157221 |
| `source_error` | 2 | 4.846813 | 5.124246 | 5.526438 | 5.165833 |
| `source_error` | 3 | 4.846813 | 5.125298 | 5.527072 | 5.166394 |
| `uncertainty` | 0 | 4.846813 | 5.120451 | 5.527689 | 5.164984 |
| `uncertainty` | 1 (selected) | 4.846813 | 5.120451 | 5.524383 | 5.163882 |
| `uncertainty` | 2 | 4.868027 | 5.131363 | 5.507635 | 5.169008 |
| `uncertainty` | 3 | 4.865187 | 5.149291 | 5.539207 | 5.184562 |
| `drift` | 0 | 4.840610 | 5.133121 | 5.528256 | 5.167329 |
| `drift` | 1 | 4.880524 | 5.140137 | 5.524177 | 5.181613 |
| `drift` | 2 | 4.863003 | 5.147602 | 5.537566 | 5.182724 |
| `drift` | 3 (selected) | 4.889842 | 5.100598 | 5.508642 | 5.166361 |
| `parameter_retention` | 0 | 4.899140 | 5.144953 | 5.527040 | 5.190378 |
| `parameter_retention` | 1 | 4.899149 | 5.144950 | 5.527041 | 5.190380 |
| `parameter_retention` | 2 (selected) | 4.899126 | 5.144972 | 5.526255 | 5.190118 |
| `parameter_retention` | 3 | 4.899932 | 5.144638 | 5.527435 | 5.190668 |

Only 3/4/5 IDs have scored labels by budget; the other 3/4/4 IDs remain unscored,
not zero-error or dropped successes. The selected proxy recipes are 1/1/3 for
Source error/uncertainty/drift, and parameter recipe 2 uses the 0.1/1 pair.
Recipe order and meanings are defined above; these are conditional tuning
choices, not evidence of optimality, convergence or independent effectiveness.
Some recipe scores differ very little and selection is sensitive to this small,
nonrandom cohort. No grid was extended after observing these outcomes.

Fresh matched Kaggle Adaptive/FT/Fixed references and remaining baseline/ablation
runs are now executing in the original serial batch. Do not pool prior Colab
target scores into a cross-runtime ranking. Full matched analysis, uncertainty,
proxy relationships, state verification, multipart transfer and CHARGED replication
remain pending. No Final lock/evaluation, local training or autonomous merge.

[Exact results, identities and remaining limits](issue23-proxy-calibration-evidence.json)
· [complete calibration metadata/proofs package](https://drive.google.com/file/d/159MLuJqqhqAuutBnsx3kGZohmtZMKbjb/view).
Anonymous readback passed exact bytes/hash, ZIP CRC and every member fingerprint.
Earlier 149/529 partial snapshots remain unchanged historical progress evidence.

The controller dependency has a different reconstruction-envelope hash on Kaggle:
`63018fae…` versus local recovery `a28df0ff…`. Investigation found all 276 original
run rows identical. Only three absolute checkpoint paths, the reconstruction-code
commit and its elapsed time differ. Both original matrix/proof pairs and the five
leaf differences are preserved; expected hashes were not edited to hide the
mismatch. This calibration binds the exact Kaggle envelope and its matching proof.

Historical staging snapshot:

260 independent fixture tests passed locally and on Colab, with local lint/format/
diff checks. The actual code is `5ad9db6ad2f4137021a05a44fd0290bbdb9afac9`.
Ubuntu/Windows CI passed for this code. Proxy/parameter calibration is staged in
a serial queue and has not launched at the recorded progress snapshot. It must wait
for successful controller completion and independent verification; a batch launch
is not evidence of completion. Full matched baselines/ablations and CHARGED,
capacity acceptance and independent immutable Final lock remain pending.

Code increment SHA-256: `ce115ed31270850c95457751b62c9b774182108e8d08fbf1ef74260767e096c3`.
Profile SHA-256: `23823e3fe6c942ed35fc79724163e6be6345e3c44061f0f6445030fbf145486d`.
The output directory must be new:
`/content/qyroven-i23-proxy-calibration-20261026-v1`.
The serial queue binds the completed controller matrix hash and verifier before
launch, records its exact command and blocks on failure. See the controller
handoff for temporary backup distribution and timing/fixture-overlap limitations.
