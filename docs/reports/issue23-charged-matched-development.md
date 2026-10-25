# Separate-city supplementary Development replication

Issue #23 / PR #52. Pre-execution scope: reproduce the complete primary-selected
comparison recipe on all six CHARGED Development city scopes. This is
configuration-transfer replication, not city-specific retuning, independent Final
validation or a claim that publisher preprocessing was causal. Shenzhen remains
separate from the other five cities because of possible UrbanEV site overlap.

Use the [actual outcome-blind cohorts](issue23-charged-development-cohort.md):
three selected ready Development sites per budget/city, 7/14/28-day histories,
seeds 42/43/44 and 90 scheduled days in publisher-local-naive time. There are
54 entity-budget combinations / 162 paired seed units. Every required main method,
nine baselines and five ablation categories must be present, with exact aliases
and any Bmin7 block-size bridge inherited from the primary collection. Depending
on the primary evidence recipe this means 14 or 16 unique variants, hence 2,268
or 2,592 actual target runs. No outcome-driven city/site/zero exclusion.

`tools.charged_matched_development` accepts the fingerprinted completed primary
analysis and a fingerprinted city cohort. Recompute the cohort selection from
current accepted metadata, verify every input manifest and common Source
population/clock/deployment across budgets, and reject cross-city bindings.
Primary selection transfers only numerical settings: Source duration, controller
recipe, Fixed Retention lambda and proxy/parameter recipes. It never loads
UrbanEV weights, models, labels or target records.

Train three new Source models per city using that city's fixed allowed Source
population and pre-deployment examples only, with the primary-selected duration.
Use the resulting city checkpoints across its target budgets and comparison
methods. The uncertainty ensemble uses those three same-city frozen Source
members. Target clones are isolated per site/budget/method/seed. Three candidates,
retention formula, frozen encoder/latent scale, update schedule, label gates and
prequential decision order remain unchanged in the shared runner.

A standalone city CLI permits honest capacity management across the authorized
Colab/Kaggle resources without pooling datasets or evading quotas. The prespecified
execution order is JHB, SPO, MEL, LOA, SZH, AMS, prioritizing smaller Source scopes
before the largest. Do not vary order using observed errors or choose favorable
seeds. New outputs only; preserve failures and all completed checkpoints.

These runs assess whether a primary-selected configuration behaves similarly on
other published data, not whether each city has independently optimal Source
convergence, proxy thresholds or controller settings. No per-city search is
silently granted to one comparator. The finite primary grid endpoints and
publisher/time/overlap limitations remain. Runtime capacity is a risk until
measured; missing cells become explicit shortfalls, never silently dropped.

Record Source/input/cohort/code/primary-selection identities, config/seed,
checkpoint/latent metadata, forecasts, arrival/update/decision events, optimizer/
RNG state, candidate/audit steps, reset peaks and costs. Source setup and ensemble
inference count toward actual cost; backup I/O is separate. Independent complete
artifact verification, paired issued/scored origin sets and downloaded state
checks remain required. City tables and intervals must stay separate, with no
pooled six-city number labeled independent external validation.

## Current status

277 local fixture tests pass with Ruff lint/format and diff checks. The six
cohorts were actually generated and authenticated, but this supplementary
Source/target training has not started. The primary controller/proxy/matched
jobs must finish and authenticate their selected recipe first. No local real-data
training, Final evaluation, configuration-lock approval or merge.
