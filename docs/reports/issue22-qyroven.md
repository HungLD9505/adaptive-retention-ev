# Issue #22 — independent baseline implementation and Development execution

Execution started 2026-10-25; continued 2026-10-26. Training/replay, artifact verification and Drive persistence completed for UrbanEV and all six CHARGED cities. Technical implementation is ready for review; scientific calibration/acceptance is pending.
No merge, Final evaluation, configuration lock or claim of effectiveness.

## Review scope

The implementation independently adds the nine Report 1 baselines and five ablation
categories to the #21 runner. Read [the baseline contract](../data/BASELINE_CONTRACT.md)
for definitions, genuine aliases, candidate budgets, proxy formulas and unvalidated
calibration choices. [Related-method feasibility](related-method-feasibility.md)
distinguishes these comparisons from reproductions of external papers.

The branch starts from dev `7a57e9e8954eb8fcdc0809b1d7f02f6c32753a0c`, locally
integrating the author's pending #47/#49/#50 dependencies with normal Git merges.
No implementation from Hung was copied. Those dependencies require review and
integration first; refresh this branch against integrated dev before its merge.

- `ev_baselines/`: Seasonal Naive, method-specific policies, parameter-retention variant.
- `ev_runner/`: reusable forecast/score/update/boundary/audit/resume machinery.
- `tools/comparison_matrix.py`: declared CUDA-only Development comparison driver.
- `notebooks/issue22_development.ipynb`: clean-runtime reproduction instructions.

## Actual execution profile

Runtime v2 code SHA: `cceab803f6898d1b1192edc74d49a762670e426b`.
Colab Tesla T4, Python 3.13.16, PyTorch 2.11.0+cu130. Main comparison seed42;
Source ensemble seeds42/43/44 are **not three replications of the comparison**.
Each namespace has independent Source weights and one initial epoch over its full
allowed Source pool. Each target has three initial epochs and one online epoch per
newly arrived complete day. Budgets7/14/28, 43 daily forecasts, lambda0/0.01/0.1,
block14/Bmin7/segment3/2,000 bootstrap resamples/alpha0.05/delta0; block ablations
use7/28 days. All choices precede scores and remain unvalidated Development examples.

Select the lexicographically first Development entity with trainable prefix examples
in every budget. This does not inspect future activity/errors. It is a technical
smoke cohort, not an official cohort or a rule excluding inactive sites. UrbanEV and
the six CHARGED cities remain separate; SZH is separately interpreted and is not
claimed as independent geographical validation. Upstream preprocessing/timezone and
possible physical-location overlap limitations remain unchanged.

### UrbanEV v2 — completed

Run `qyroven-i22-urban-20261026-seed42-v2`: target1001, 14 unique methods/variants ×
three budgets =42 cells. Every cell issued/scored43/43 days. Driver elapsed172.982s,
excluding reused Source pretraining and package/upload work. This is not an estimate
for all targets or an official experiment-matrix runtime.

Source seed42 reuses the identified #19 checkpoint
`28d61828a35be69b04f907df9128e7cf4743868060addd113cc61b60363e2905`;
seeds43/44 reuse the identified v1 Source checkpoints. Their actual hashes, commands,
configs and original training costs are retained in matrix/Source reports.

The earlier v1 run is preserved but superseded: v2 removes unused Source loading
from Target-only/Naive, resets random initialization after Source loading to pair
random starts, and separates shared replay-index preparation from cell timings.
These corrections were not selected by favorable scores. Do not combine v1/v2
scores or present v1 cold-start timing as a fair method comparison.

### UrbanEV + CHARGED — real GPU execution complete

All six prepared-input archives downloaded and SHA-256 verified against
`data/releases/DATA-v1-20261019.json`. The v2 driver completed AMS → JHB → LOA →
MEL → SPO → SZH sequentially on the same T4. Each namespace has14 unique
methods/variants ×3 budgets =42 cells, all43/43 forecast/scored days.

| Namespace | Development target | Source examples per seed | Cells | Issued/scored days per cell |
|---|---|---:|---:|---|
| urbanev-SZH | 1001 | 65,888 | 42 | 43/43 |
| charged-AMS | 0 | 134,640 | 42 | 43/43 |
| charged-JHB | 12 | 2,340 | 42 | 43/43 |
| charged-LOA | 1 | 12,330 | 42 | 43/43 |
| charged-MEL | 12 | 3,060 | 42 | 43/43 |
| charged-SPO | 11 | 2,610 | 42 | 43/43 |
| charged-SZH | 1 | 79,740 | 42 | 43/43 |

Total 294 cells and 12,642 forecast-day vectors. There are21 identified Source
checkpoints across seven namespaces (three seeds each), including the reused
UrbanEV Sources. CHARGED trained18 new Sources, one epoch each. This is still only
**one comparison seed and one target per namespace**, not the mandatory multi-seed,
full-cohort experiment. Actual runtime/config/cost/metrics are in the complete
[execution summary](https://drive.google.com/file/d/1DE1grlvRgskV1kfCUjbkTKuFs11spG0d/view)
(180,293 bytes; SHA-256
`3efe54d6f98c01eeead8b01fbf5630f1e743295dda10c4b482c70f6e20159067`).
The summary was downloaded back and its hash verified. All six CHARGED archives
are now uploaded and hash-checked; Drive was flushed/unmounted, then connector
metadata confirmed the expected sizes and inherited shared access for all23 files.

AMS prefix-selected site0 has zero energy in the scored portion inspected so far.
Its smoke exercises the zero-activity case. This cannot establish comparative
scientific effectiveness or justify removing sites by future activity. Additional
prefix-defined targets and seed replications belong to Development validation.

The longer UrbanEV run now exercises a complete real audit block: budget7 Adaptive
has14 paired days following the December29 switch (December29–January11).
The audit stays retrospective and is not supplied to the controller. This extends
the earlier #21 29-day smoke, whose late switch had only one subsequent day; it
does not retroactively change that earlier report or lock a harmful-switch threshold.

## Persisted UrbanEV evidence

[Team artifact folder](https://drive.google.com/drive/folders/1HsV73P0KPRtZdtfur80qH2jJM9EG95W6)
contains the full UrbanEV v2 ZIP, complete matrix and SHA-256 manifest. Exact files:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| [Full UrbanEV ZIP](https://drive.google.com/file/d/1tG0NxvTbr8aC2awFcebop6tJuzHnTpD-/view) | 2,323,714,748 | `6117b9184578db2b9a1a39c54a70bc2e04cfd32c07ac948fceeae63d90332e55` |
| [UrbanEV matrix](https://drive.google.com/file/d/1HJ3xBbvF9PWkJB5xKP9wRpYRfeRF8MaP/view) | 799,741 | `a1a8ec96074402564671e952c184e499eb4e30aa8f9e7b10a4e0cfe0a5e7566e` |
| [Engineering spot-check ZIP](https://drive.google.com/file/d/1QTxLBXwEHD6yhPFT6WKr6GIHGamDHHgs/view) | 105,217,167 | `83e8d5eb798b786b4ced08ee4556a01cf092d0b40de13200259f1d8c02e8ea8c` |
| [Superseded UrbanEV v1 ZIP](https://drive.google.com/file/d/1ihNmRLK-6BFMFN56KxuetNf4JiTQV37c/view) | 2,847,258,880 | `9b0797533b3fb65fb269e6ba8a6986088a5f29df658d26d2fd86012d1843b3f9` |

The full ZIP contains every UrbanEV run and referenced Source checkpoints under
`source-dependencies/seed*/final.pt`. Original matrix paths describe the execution
machine. After relocation, explicitly map those verified checkpoint hashes to new
local paths in a **new** Source-pool manifest; preserve the original matrix and its
hash. A clean notebook retraining is not a byte-identical reconstruction of reused
checkpoints on a different environment.

The superseded v1 archive preserves all earlier run outputs and the original Source
reports/configs/logs. Its embedded matrix hash is
`fa95334fc72a820fc345171a07f0513d8a4ae33c0fa049b80030c534921154ca`,
matching v2's declared Source-pool parent. Source43/44 checkpoint hashes are
`b24b7340cb0e96433aa8bf4be33f3aa58459af36b799f075b1fed567aa21f7e7` and
`ab5458bd9e798cc2f0fcaf5b28cf92997fecde6cdf5397bd8ae3e0e0c9a439ad`.
The v1 comparison results remain superseded regardless of whether individual scores
look better; no run is selected on that basis.

The stdlib post-hoc verifier in pending #52 independently hashed5,670 daily files
across all42 UrbanEV cells and recomputed every candidate's original-unit MAE/MSE
from saved predictions and identified Development labels, with arrival checks;
deployed MAE/RMSE/counts/commit chains matched. This is independent calculation in
the Colab runtime, not a separate data-source validation.

The full ZIP exceeds the connector's256 MiB download limit. The fixed engineering
spot-check contains all daily files for budget7 Adaptive, Target-only and Seasonal
Naive, chosen by method/budget rather than scores. It was independently downloaded
back, checksum/ZIP CRC checked,405 daily files authenticated, all three runs' scores
recomputed against local identified inputs, and final checkpoints safely loaded on
CPU with `weights_only=True`. No real-data training ran locally. The full ZIP was
hash-verified on the mounted Drive; it was not downloaded back in full.

## Verification and remaining acceptance

Local:188 offline fixture tests pass; Ruff lint/format pass. This includes independent
baseline/fallback/state, Source-free initialization, lambda0 gradient equivalence,
proxy availability and checkpoint/policy restoration tests. Colab v2 also ran the
188-test suite and Ruff before training. Tests do not prove upstream data causal.

Completed CHARGED verification authenticated34,020 daily files and independently
recomputed every candidate/deployed original-unit score with arrival gates. Across
both matrices this is39,690 authenticated files. All21 Source checkpoints were
hash-checked and safely reloaded on CPU: namespace/seed binding, one completed
epoch, architecture and finite nonnegative64-dimensional latent scales matched.
The complete CHARGED matrix, Source verification and verification summaries were
downloaded back; their hashes match the stored catalog. The six multi-GB CHARGED
ZIPs were hash-checked on the mounted Drive and checked by metadata/size readback,
not downloaded back in full.

Pending: peer review/integration; assess proxy estimators/mappings and parameter-loss
calibration with comparable finite Development budgets; measure the complete
mandatory matrix cost; obtain independent configuration-lock approval before Final.
One target/main seed per namespace does not satisfy scientific validation across
the full cohort/seeds. Issue #22 stays open while these acceptance gates remain.

## Download and review entry points

- [Artifact catalog with every file/link/size/SHA-256](issue22-artifacts.json).
- [Compact execution evidence](issue22-execution-evidence.json).
- [Source verification](https://drive.google.com/file/d/1rrXt3ZoPnMAeMxUyorX-jRSv31KjLW9D/view).
- [CHARGED matrix](https://drive.google.com/file/d/1lUmw81ACL91L1BOKOvSYvMMzuwtWc-fB/view).
- [CHARGED post-hoc verification](https://drive.google.com/file/d/1Cg7Jt3nUVutuK9D4jKV7AhqD2-C9_t1w/view).
- [Environment/pip freeze/GPU/code](https://drive.google.com/file/d/1vUM33rMcvPDUaeZ0O78_9nhYyQITnlu_/view).
- [All artifact checksums](https://drive.google.com/file/d/15aIQ_RAcTWHvU0k32CSez2zyilqIhb3q/view).

Original run directories, checkpoints, input files and raw archives were retained.
Only redundant local upload-staging ZIP copies were released after verified Drive
copies to avoid exhausting the Colab disk. The archived ZIP contents remain intact.

CHARGED matrix elapsed1,758.074 seconds including18 new Source subprocesses and
its shared preparation/252 cells; UrbanEV v2 elapsed172.982 seconds reused all three
Sources. Packaging/upload and independent verification are additional cost. These
scopes differ; neither number is a fair cross-dataset performance comparison or
a full-cohort capacity estimate. Current dense daily-state storage requires a
separate full-matrix feasibility decision before Final; mandatory methods, budgets
and seeds must not be silently dropped to meet capacity.
