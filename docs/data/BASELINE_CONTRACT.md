# Required comparisons — Issue #22

Report 1 §8.1 requires nine baselines alongside the proposed adaptive method. This
implementation uses the common #21 event order, input identities, fixed scaling,
complete-label gates, missing-history schedule and daily resume machinery. Method
names identify research definitions; none is claimed as a related-paper reproduction.
The current Development profile is an executable example, not a Final configuration
lock or evidence of superiority.

## Methods and actual candidate budgets

| Method ID | Initialization and update | Selection / cost |
|---|---|---|
| `adaptive` | Source weights, latent retention | Three candidates; #20 confidence rule |
| `seasonal_naive` | No learned model; known target history only | One forecast, zero SGD steps |
| `target_only` | Random GRU, target data only, lambda0 | One trained candidate |
| `frozen_source` | Source GRU, no target adaptation or online updates | One frozen candidate, zero SGD steps |
| `full_finetuning` | Source GRU, lambda0 | One trained candidate |
| `fixed_retention` | Source GRU, fixed positive lambda | One trained candidate |
| `online_best` | Same three candidates/start/data/normalization/order/budget as adaptive | Lowest mean daily MAE; no bootstrap; Bmin still applies; exact ties prefer active/nearest then fixed order |
| `source_error` | Same three-candidate framework | Map recent frozen-Source MAE on arrived complete labels to next-block level |
| `uncertainty` | Same framework plus a fixed identified Source ensemble | Map Source prediction dispersion; include ensemble inference and extra pretraining cost |
| `drift` | Same framework | Map available-history descriptor discrepancy; mapping direction is configurable |

Target-only and Seasonal Naive do not load a Source model; their method-specific
Source-use flag is false. A common comparison Source identifier may remain in the
experiment context for provenance, but it does not enter those predictors. Random
initialization is seeded independently of Source-loading side effects, pairing
Target-only with the no-initialization ablation.

Source models remain separate by dataset/city and main training seed. There is no
UrbanEV → CHARGED Source transfer in this design. The smoke uncertainty ensemble
uses Source seeds42/43/44 from the **same** allowed Source population, with unique
identified checkpoints and the same architecture. The main Source seed matches the
run seed. Members never train on target/future labels.

## Seasonal Naive and fallback

For hour t, prefer the available value at t−168h. If unavailable, try t−24h, then
use the mean of known pre-origin target values. If none exist, predict zero and
record that fallback. A zero forecast is not an assertion that an unknown label
was zero. Preserve observed zero-valued history as valid data.

History is populated from accepted allowed-prefix examples and masked predictor
history. Only complete labels released by the common runner are added afterward.
Dictionary keys deduplicate repeated timestamps. It never fills labels or uses a
future value in a fallback mean. Prefix hours not recoverable from accepted example
records cannot be invented; weekly coverage/fallback counts are recorded in state.
A different access policy using full hourly artifacts would require explicit review.

## Proxy definitions and calibration boundary

All proxy selection uses the same block boundary and complete-day comparison
population. Prediction-time signals are saved with the origin; Source errors are
created only when the complete label vector arrives. Late/future/unscored days are
excluded from the block's decision signals. Audit errors never enter any selector.

- Source error: mean absolute error of the frozen Source forecast on the fixed
  normalized target scale, averaged over eligible days in the block.
- Uncertainty: for each saved predictor input, population standard deviation across
  at least three frozen Source-member forecasts, then mean over the24 horizon steps.
  This is seed-ensemble dispersion, **not calibrated predictive coverage**. Its
  relation to Source error and its retention mapping require Development assessment.
- Drift: the descriptor is observed-history mean, maximum and zero fraction. Fix the
  coordinate mean/std from allowed-prefix training-input descriptors; zero std uses
  denominator1. If no trainable prefix exists, use the first predictor-visible input
  as the frozen reference. Signal is the root mean square standardized discrepancy.

Two explicit thresholds choose one of three bins. `proxy_order` maps bins to the
three retention levels; both increasing and decreasing mappings are possible. There
is no rule asserting that greater drift/uncertainty/error must lower retention.
The smoke thresholds are Source error0.1/0.5, uncertainty0.01/0.05 and drift0.5/1.5,
with ascending level order. They are **unvalidated examples**. #23 must assess finite,
comparable tuning budgets on Development and lock estimators/mappings before Final.
One example mapping run does not satisfy that scientific calibration gate.

## Five ablation categories

| Ablation | Explicit definition |
|---|---|
| Without confidence | Replace LCB by observed mean improvement, retaining Bmin/delta and tie order. With delta0 this is exactly `online_best`, so reuse that run. For nonzero delta, run separate `without_confidence` with the mean-margin gate. Never label a mean as an LCB. |
| Fixed lambda | Exactly `fixed_retention` when lambda/config/input/seed match; reuse the same run. |
| Parameter retention | `parameter_retention`: replace latent penalty with elementwise mean squared difference over **encoder parameters only**; Source parameters detached, forecast head excluded. Divide by total encoder element count, not layer count. |
| Different block size | `block7` / `block28`: same adaptive rule, starts, update schedule and candidate levels, with7/28-day blocks respectively. Example Bmin7/segment3 remains supported; tuning still belongs to Development. |
| Without Source initialization | `without_source_initialization`: random target initialization, retaining the frozen Source reference/latent scale and confidence controller. It tests weight initialization, **not removal of all Source knowledge**. Target-only instead has lambda0 and no Source retention. |

Parameter-loss units differ from standardized latent-loss units. Its positive lambda
values need their own Development assessment with a comparable finite tuning budget;
reusing smoke values does not establish a fair final calibration. The primary latent
formula is unchanged. These ablation definitions are explicit proposals for peer
review, not silently accepted method changes.

With delta0, the example has14 unique methods/variants: proposed + nine baselines +
parameter/no-initialization/two alternative block sizes. The two equivalent ablations
refer to existing runs and are not double-counted.

## Execution, accounting and acceptance

`tools.comparison_matrix` predeclares namespace, seed list, horizon and method list.
It picks the lexicographically first Development ID that is ready and has trainable
**initial-prefix** examples in all budgets; it does not filter on future activity,
error or full-release zero statistics. This is a technical-smoke selection rule,
not an official research cohort or exclusion policy.

Source pretraining occurs before the comparison runs. Budget variants must identify
the same Source population. The driver records subprocess wall time for new Source
training, shared replay preparation time, per-cell wall time including initialization,
actual candidate steps/memory and separate audit/proxy costs. Dataset/city scopes are
independent. Checkpoint resumption requires matching method/input/code/environment
bindings. Cache only validated immutable prefix/predictor data; the delayed-label
provider indexes row identity/time headers without decoding future energy arrays.

`frozen_source` performs no initial/online training. Seasonal Naive adds released
history without counting it as an optimizer step. Single-model baselines do not
train three unused models. Three-candidate controllers share the same candidate
budgets. Input validation, reused Source training, ensemble preparation, artifact I/O
and audits must be included or explicitly separated in capacity accounting.

Routine tests use independent fixtures and tiny CPU updates. Real-data CLI runs
require CUDA. No Final performance, dataset exclusion or configuration selection is
performed by a technical smoke. #22 stays open until all methods have real evidence,
proxy/variant review and the required Development validation are accepted.

Related-paper feasibility is recorded in [the primary-source assessment](../reports/related-method-feasibility.md); no custom proxy is labeled as an external-method reproduction.
