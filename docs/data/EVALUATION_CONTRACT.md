# Evaluation accounting — Issue #23 (review proposal)

Report 1 §8.2–8.3 requires original-unit MAE/RMSE, station-first analysis, gain/NTR,
at least three seeds and uncertainty accounting for station/time dependence. The
helpers implement metric accounting and exploratory paired station/calendar-block
intervals for selected Development cohorts. They do not access Final, choose
hyperparameters or certify a configuration/analysis lock.

## Metric and pairing units

Each `DailyError` describes one complete24-hour vector. MAE and MSE are computed
from stored normalized predictions multiplied by the fixed target scale, against
original kWh labels. Do not impute labels. Over a period, average daily MAE and take
the square root **after** averaging daily MSE. Averaging daily RMSE is incorrect.

For each method and Target-only comparator, require exactly the same scored origins;
never silently intersect convenient days. Seed replications for a station also
require identical scored origins. Missing cells are shortfalls, not implicit zeros.

The proposed NTR unit is one station within a separately identified namespace,
history budget, evaluation period and initialization stratum. First average each
method's period MAE across the declared paired seeds for that station, then compute
`gain = (MAE_target_only - MAE_method) / MAE_target_only`. NTR is the fraction of
stations with negative gain. Report the complete station gain distribution and
absolute gap `MAE_method - MAE_target_only` in kWh; no tolerance is silently inserted.
This explicitly defines a proposal for review before configuration lock.

When the station's mean Target-only MAE is exactly zero, gain/NTR membership is
undefined. Report the absolute gap and number of zero-baseline stations separately;
exclude those stations from the NTR denominator. Never add an epsilon to manufacture
a finite ratio. If every denominator is zero, NTR is null, not zero.

Macro MAE and RMSE give every station equal weight after seed averaging. Macro RMSE
means the mean of station/seed period RMSE, not square root of a pooled fleet MSE.
Never pool UrbanEV with CHARGED cities or merge SZH into an independent-geography
number. Keep `source_checkpoint_only` and ordinary adaptation strata distinct.

## Uncertainty and configuration gates

`station_first()` requires at least three unique declared seeds. It deliberately
returns no population interval: station/time dependence needs paired resampling,
and one smoke station does not support a population-level confidence claim. A separate exploratory station/calendar helper is described below; it does not
turn this aggregate into a population interval. Full-method uncertainty and
accepted context/switch analysis definitions remain pending.

The full-method technical smoke has main seed42 only. Source ensemble42/43/44 does
not satisfy the three-comparison-seed requirement. The additional
[UrbanEV readiness run](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/issue23-readiness.md) has three actual comparison
seeds for Adaptive and Target-only on a shared-identity cohort, but does not replicate
the entire required baseline/ablation matrix. Full Development calibration/cohorts,
training convergence choices, comparable finite tuning budgets, exact mandatory
matrix and compute/storage feasibility must be reviewed before an immutable lock.
Independent approval of config/code/data/cohort/checkpoint identities is required
before Final. These helpers do not grant that approval or enable Final access.

## Read-only artifact verification

`python -m tools.verify_comparison --matrix MATRIX --inputs-root INPUTS --output NEW_JSON`
authenticates every daily file and chronological commit chain, checks the input
manifest/entity/label fingerprints, rejects Final roles, and decodes labels only for
the identified Development target. It recomputes every candidate's original-unit
MAE/MSE from saved predictions/labels, checks availability timestamps and confirms
aggregate deployed MAE/RMSE and count identities. No model is trained or substituted.
It does not prove upstream publisher preprocessing was causal or independently
establish true collection/availability times. A valid stored fixture is not research
performance evidence.

## Measured storage risk

UrbanEV technical matrix v2 has42 cells ×43 days and2,843,035,372 raw output bytes;
its ZIP is2,323,714,748 bytes. Dense daily model/optimizer/RNG states dominate.
The accepted input entity summaries contain1,168 ready Final IDs across the seven
namespaces at budget7 (metadata counts only, no Final labels inspected). Simply
scaling this one target's dense storage to1,168 targets, three comparison seeds and
roughly90 replay days yields about20 TB raw, before extra tuning, audit variation,
Source artifacts and replication overhead. This is a rough capacity warning, not
a measured complete-matrix prediction or a committed cohort.

A full run cannot be authorized from the smoke's172.982-second cell-driver timing:
that reused Source models, uses one target and excludes upstream preparation,
packaging/upload and independent verification. Concurrent packaging/verification can
also contend for I/O during CHARGED smoke. A measured, feasible artifact-retention
policy and total cost projection remain required; do not silently shrink mandatory
budgets/methods/cohorts to fit storage or claim the cost gate passed.

## Opt-in latest-state retention for new Development runs

The new readiness config explicitly sets `state_retention: latest`. Default `all`
and every historical run remain unchanged. Every tick first durably commits its
full model/optimizer/RNG/pending-label/controller/audit state, forecasts, events and
hash-linked manifest; only then releases older full-state files within that new
run. All forecasts/events/commit files and historical state-hash commitments remain.
The latest full state is mandatory for resume. Policy is bound in the exact config;
changing policy across resume fails. Pending incomplete transactions still fail
closed. POSIX directory entries are synced before older states are released.

The verifier reports physically checked files separately from intentionally omitted
historical state files. It never claims to rehash absent bytes. Older model snapshots
cannot be loaded directly under this mode; regenerate history from the identified
Source/input/config when needed. This changes persistence, not forecasts, SGD,
controller decisions or audit behavior. Fixture parity, crash/failure and exact
resume checks are required; real CUDA resume and measured storage savings are
recorded only after execution. This policy is proposed for review before Final.

## Exploratory Development uncertainty implementation

`paired_station_time_interval` resamples station IDs and circular blocks on the
full scheduled calendar. One shared calendar draw per replicate preserves common
calendar shocks across sampled stations; missing dates remain missing. Paired seed
errors are averaged within station/day first, then days within station and stations
equally. Seeds are fixed replications, not independent station samples. The estimator
is the original-unit method-minus-comparator MAE gap. It is distinct from the
controller's one-sided normalized LCB and cannot affect deployed predictions.

The proposed analysis profile fixes seven-day segments,2,000 draws,95% two-sided
marginal percentile intervals with linear quantiles and seed20261026. It is an
exploratory Development definition, not an approved Final analysis lock. If any
replicate has an empty sampled station mean, the interval is null and the count is
reported; no zero filling or hidden repeated redraws. Small/nonrandom/possibly
colocated IDs, circular seams, nonstationarity and multiple comparisons limit
interpretation. Do not interpret such intervals as population guarantees or use
significance claims to select a favorable setting. Weekday/weekend summaries and
continuous valid-history coverage are descriptive; sparse/dense thresholds and
harmful-switch margins still require Development decisions.

## Prefix load-density grouping proposal for Development

Report 1 requires sparse/dense analysis groups with thresholds established on
Development. `tools.development_contexts` proposes an explicit descriptive rule:
for each namespace and history budget separately, compute the fraction of valid
initial-prefix hours with positive energy. Use the median across all ready
Development entities, giving one vote per entity; values strictly below the median
are sparse, ties and larger values dense. Report valid-hour coverage, tie counts
and group sizes. With a tied population one group may be empty; do not force a
balanced split or remove zero-activity entities. No valid prefix hours means an
undefined group, never zero density.

This reads authenticated entity-prefix metadata only. It does not use online
forecast errors, release-wide activity, Final values, or change cohort eligibility,
training, calibration or controller inputs. Missing hours are excluded from the
fraction's denominator and coverage must accompany it. Positive-energy frequency
is an operational load-density descriptor, not physical charger occupancy,
energy magnitude or proof of behavior change. Publisher-filled values remain a
limitation. Thresholds vary by namespace/budget; comparing different budgets is
not a controlled history-budget effect. The rule and resulting Development
thresholds require independent review before any Final lock. They do not replace
weekday/weekend or initialization-stratum analysis.

The selected-collection analysis also implements fixed calendar days 1–30,
31–60 and 61–90 and descriptive same-block proxy/candidate performance
relationships. Their explicit profile identities, availability checks, pairing,
undefined-correlation handling and cost boundaries are documented in the
[Development analysis extension handoff](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/issue23-analysis-extensions.md).
These are post-hoc Development proposals, not independent Final analysis approval.
