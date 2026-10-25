# Issue #22 — independent baseline implementation and Development execution

Execution started 2026-10-25; continued 2026-10-26. Work is in progress.
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

### CHARGED — executing

All six prepared-input archives downloaded and SHA-256 verified against
`data/releases/DATA-v1-20261019.json`. The v2 driver is executing AMS → JHB → LOA →
MEL → SPO → SZH sequentially on the same GPU. Completion is not claimed until each
namespace has its Source reports,42 completed cells and verified artifacts.

AMS prefix-selected site0 has zero energy in the scored portion inspected so far.
Its smoke exercises the zero-activity case. This cannot establish comparative
scientific effectiveness or justify removing sites by future activity. Additional
prefix-defined targets and seed replications belong to Development validation.

## Verification and remaining acceptance

Local:188 offline fixture tests pass; Ruff lint/format pass. This includes independent
baseline/fallback/state, Source-free initialization, lambda0 gradient equivalence,
proxy availability and checkpoint/policy restoration tests. Colab v2 also ran the
188-test suite and Ruff before training. Tests do not prove upstream data causal.

Pending: finish/persist/independently verify CHARGED artifacts; post exact links and
hashes; request peer review; assess proxy estimators/mappings and parameter-loss
calibration with comparable finite Development budgets; measure the complete
mandatory matrix cost; obtain independent configuration-lock approval before Final.
One target/main seed per namespace does not satisfy scientific validation across
the full cohort/seeds. Issue #22 stays open while these acceptance gates remain.
