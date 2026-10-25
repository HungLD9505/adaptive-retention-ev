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

## Current status

The original Colab queue described below was lost when that kernel was evicted;
it never produced a completed proxy matrix. All controller backup runs have since
been recovered and verified. The identified [Kaggle recovery](issue23-runtime-recovery.md)
now executes this unchanged finite proxy grid at training commit
`54131cbb8ce47f9d064b80f03956e8e62ec48346`. The most recent UI probe observed
514/1,104 completed report records and an active Stop execution control. That is
partial live progress, not a complete independently verified matrix, selected
proxy recipe, durable checkpoint backup or a new effectiveness result. The
[separately saved 149-report snapshot](issue23-kaggle-partial-progress.json)
preserves earlier progress metadata only. Full downstream references/analysis
and artifact transfer remain gated on successful completion and verification.

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
