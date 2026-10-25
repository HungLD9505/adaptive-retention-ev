# Independent implementation comparison — readiness, 2026-10-26

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
