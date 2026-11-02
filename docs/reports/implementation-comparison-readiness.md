# Independent implementation comparison — readiness, 2026-10-26

## October 27 current-head recheck

Read-only inspection of Hung's PR #72 head
`30fe7d196d9e3ede954384089790e718aa314d32` and Qyroven's
`6d3feeced568eea8bd691e41b8bb97e55ce15333` reconfirmed the material head
topology and bootstrap quantile/RNG differences described below. Fresh bounded
CPU fixtures on the newly pinned component bytes give encoder maximum absolute
difference 0 with shared encoder weights, identical retention loss
2.5089153428333866, exactly equal target gradients and absent reference gradients.
Parameter counts remain 52,376 versus 41,696 at the declared head widths.
See [current component evidence](issue23-current-hung-comparison.json).

This does not establish full-head/controller/runner parity or authorize merging
the implementations. No foreign implementation or trained weights were adopted.
Hung's current [phase handoff](https://github.com/HungLD9505/adaptive-retention-ev/blob/30fe7d196d9e3ede954384089790e718aa314d32/docs/reports/hung-e2e-phase-20261027-1045.md)
reports 362/782 new jobs completed, 302 with remote readback and 60 awaiting it;
his work is explicitly incomplete. Those counts use a different job definition
and cannot be combined with Qyroven's counts. This inspection did not independently
restore Hung's large private archives or verify live provider jobs.

The historical profiles below remain attributed to their original executions;
they are not relabeled as the newest calibrated profiles.

The Qyroven implementation was already independently committed/executed before
inspecting Hung's code for this comparison. No Hung model/controller/training code
or trained weights are incorporated into Qyroven's implementation.

Sources inspected: PR #46 head `b1f9edaa7f5c28e081159e90bedd58765afeb1a1`,
Hung's representative report/config/selection/freeze record, and the model/retention
component sources. Hung's historical training commit is `a34a49e`; later PR-head
validation is a different execution. Hung's large Kaggle/local archive has not been
independently downloaded/reverified in this comparison.

## Verified documentary differences

| Axis | Hung's declared executed profile | Qyroven executed comparison smoke |
|---|---|---|
| Dataset | UrbanEV | UrbanEV and six separate CHARGED cities |
| Seeds | 7,11,19 | Main42; Source ensemble42,43,44 |
| Development targets | 6/8/9 IDs by budget; includes missing/source-only | One common prefix-trainable ID per namespace |
| Horizon of online replay | 90 days, resumed from42 | 43 days |
| Source training | One pass, batch32 | One epoch, batch64 |
| Initial adaptation | One pass, batch2, lambda0.1 | Three epochs, batch64, lambda0.01 |
| Latent epsilon | 1e-6 | 1e-3 |
| Candidate levels / initial | 0,0.1,0.2 / 0 | 0,0.01,0.1 / 0.01 |
| Bmin / bootstrap segment / resamples | 5 / 2 / 100 | 7 / 3 / 2,000 |
| Runtime | PyTorch2.8/CUDA12.6, RTX3050Ti for representative run | PyTorch2.11/CUDA13, Colab T4 |

Hung reports69 entity×budget×seed cells (216 stages, including Source/target/resume),
with33 null-metric cells. Qyroven's294 cells count methods×budgets×namespace at one
main seed. These are different units, not a leaderboard. Input manifest hashes for
the three UrbanEV budgets match; this alone does not make scores comparable.

## Material head-topology difference

Both encoders are stock two-layer hidden64 GRUs on24×7 history. Qyroven concatenates
z[64] with flattened future calendar[120], then Linear184→64, ReLU, Linear64→24,
Softplus. Hung applies Linear120→8/ReLU to calendar first, concatenates z with that
8-vector, then Linear72→24/Softplus. This is a topology difference, not merely a
rename or hidden-width setting. Their full heads/checkpoints cannot be equated by
loading the same GRU weights. Report 1 §5.1 describes combining z and future calendar
before the MLP; reconcile the head interpretation explicitly at review before a
matched architecture experiment. Do not silently rewrite either implementation or
retroactively relabel historical results.

## Current next execution (Development only)

`configs/issue23/readiness-cohort.json` fixes the same previously declared UrbanEV
identity metadata used by Hung:6/8/9 entities across7/14/28-day budgets. Only metadata
IDs/prefix counts/manifest hashes are reused, with original commit/file hash recorded;
no future-label coverage or observed scores filter this selection. Qyroven's own
seeds42/43/44, model, Source checkpoints and diagnostic settings remain unchanged.
Adaptive and Target-only will each run90 scheduled days:138 runs,69 paired units.
This is a shared-identity readiness run, not a matched-config winner comparison,
not calibration and not completion of the full baseline matrix or Final.

It includes sparse histories and `source_checkpoint_only`; undefined scales remain
blocked. Zero-score outputs remain null and are reported. Source-only versus
initial-adaptation strata remain separate. Before future performance comparison,
fix the same architecture/config/seeds/update order/cohort/period and tolerances;
first compare encoder/loss/gradient fixtures, then decisions and replay traces.

## Executed independent component fixtures

`tools.compare_hung_components` imports a separate, byte-pinned Hung checkout only
for bounded CPU fixtures. Routine CI does not download or depend on that checkout.
Actual evidence is in [component evidence](implementation-component-evidence.json).
With shared encoder weights and synthetic input, maximum encoder difference was0.
Both latent-retention implementations returned2.5089153428333866, matching an
independent scalar sum; target gradients matched exactly and neither reference
received gradients. Shared constant-score cases passed for insufficient evidence,
equal errors/keep, a clear challenger and equal-LCB nearest-level tie-breaking.

Full model parameter counts differ: Qyroven52,376 versus Hung41,696 under their
reported diagnostic head widths. This is not a performance comparison. The CPU
comparison used PyTorch2.11, not Hung's historical2.8 training environment.

Bootstrap conventions differ beyond config values: Qyroven uses linearly
interpolated empirical quantiles; Hung uses an order statistic, ceil(alpha×R)−1.
Bootstrap RNG derivation also differs. Constant-score tests cannot establish
identical LCBs on varying daily scores or identical full runner traces. These
choices must be reconciled explicitly before numerical head-to-head claims.

## Capacity shortfall — explicitly unresolved

A metadata-only count of the existing #18 ready roles, combined with the executed
43-day T4 timing of all14 distinct methods, gives an illustrative full-population
projection for90 days and three seeds. This is not a new eligibility rule, approved
cohort, configuration lock or Final evaluation. No Final forecast/label rows were
decoded for this estimate.

| Hypothetical all-ready scope | Method×entity×budget×seed runs | Serial T4 hours |
|---|---:|---:|
| Development, all seven namespaces | 143,766 | 354.7 |
| Final, UrbanEV | 43,092 | 88.9 |
| Final, six CHARGED cities separately | 104,328 | 273.5 |
| Final, total | 147,420 | 362.5 |

[Calculation evidence](issue23-capacity-estimate.json) records every timing cell,
ready count, formula and input-matrix fingerprint. It linearly scales elapsed time
by90/43 and by ready entities×three seeds. It excludes tuning, Source convergence
choices, retries, shared input preparation and transfer/verification; it also does
not model compact-checkpoint I/O changes or station workload heterogeneity. It is
neither an upper bound nor a promised completion time. The previously declared
one-pass Source checkpoints are diagnostic, not convergence-selected models.

Even this illustrative Final total exceeds15 uninterrupted T4 days. A complete
experiment matrix cannot currently be called capacity-accepted on one intermittent
Colab session. Additional lawful compute/parallel execution and a documented
Development-derived, method-compliant cohort decision are review items. Do not
silently drop required seeds, budgets, methods, or CHARGED scope to meet the date.
Compact checkpoint retention addresses disk cost; it does not resolve the full
compute/lock/peer-acceptance gate by itself.

PR #46 advanced after the pinned component inspection to `e85a53c`; the two intervening
commits only add raw-archive upload/readback reports. They do not change the component
bytes compared above or authenticate the un-downloaded historical training archive.

## Re-execution interface

Run actual training on a CUDA Colab runtime, not the developer's laptop. The
readiness driver is `python -m tools.development_readiness`; its required arguments
are `--inputs-root`, `--selection`, `--selection-sha256`, `--source-pool`,
`--source-pool-sha256`, and a fresh `--output` directory. The committed selection
hash is `6884857291b79b35f83cc7d78b6fc7a2b5fe0283ebe85c0321a5eb1a5ee283f0`.
It rejects changed manifests, prefix counts, roles, Source populations and seeds.

The execution archive contains the exact Git bundle, cohort, original Source-pool
matrix, three Source checkpoints, test/training logs, predictions/events, linked
commit manifests, latest full states and the read-only postprocessing script. For
a new machine, copy the Source-pool JSON to a new file and replace only each Source
`path` with its extracted `sources/seed{seed}.pt` absolute path. Verify each file
against the original `checkpoint_sha256`, then pass the new path-only pool's SHA-256
explicitly. Preserve the original matrix. This path rebinding is not retraining or
selection of new Source weights. Download the same #18 input snapshot separately.

For verification only, use `tools.verify_comparison` with the extracted
`readiness/matrix.json` and the identified #18 input root. Its verifier does not
require the old absolute Source paths. Exact GPU continuation additionally requires
the recorded code/config/environment binding; loading a checkpoint on CPU is only
an integrity check, not a demonstration of CUDA resume on another machine.
