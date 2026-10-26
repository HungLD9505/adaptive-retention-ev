# Authenticated selected Development collection and analysis

Issue #23 / PR #52. `tools.analyze_matched` is read-only. It assembles selected
rows from the completed Source-duration, Fixed Retention, Adaptive Controller,
proxy/parameter and missing-comparator matrices. Every matrix must match its
independent verifier fingerprint, complete population, counts, scores and commit
chains. The source/controller dependency hashes and common cohort must agree.
No Final data, best-seed selection or retrospective forecast replacement.

Recompute all five families' selections using the predeclared station/seed-first,
equal-budget scores. Never trust an edited winner pointer. Require every expected
method/station/budget/seed cell, including nulls, and the correct actual config,
common training schedule, input/Source family and unchanged core algorithms.
Without Confidence aliases Online Best only at delta0. The bridge is a separate
diagnostic reference when needed, not a second tuned main Adaptive method.

For each selected run, rehash the actual daily forecasts/events and commit chains,
check the authenticated local run report, follow each saved prediction identity
into its score event and reconstruct original-unit daily MAE/MSE. Compare the
**full actual ordered issued origins and scored-origin sets**, not counts or a
silent intersection. The previous independent verifier has already recomputed
original-unit residuals from arrived complete labels; the collection checks its
fingerprint and exact scores before trusting it. This collector does not itself
re-read label arrays, rehash checkpoint tensor contents or prove publisher causality.
A complete downloaded-state check remains required after export.

## Aggregation and interpretation

- Average paired seeds within station and stations within budget. Keep budgets
  separate; their station IDs differ. Report MAE and mean per-seed/per-station RMSE,
  not a misleading pooled-hour RMSE under the same label.
- Retain unscored entities explicitly. Mixed score availability across seeds,
  absent cells, altered bindings and coverage differences fail closed.
- NTR is station-level after averaging paired-seed MAEs against Target-only.
  Target-only MAE0 has no relative gain/NTR classification: report absolute gap
  and zero-baseline denominator counts, not a substituted denominator.
- Report initial-adaptation versus no-initial-trainable strata separately, with
  method-specific initialization in run rows. Source-checkpoint-only targets are
  not silently pooled as initially adapted targets. Also retain weekday/weekend
  station-first slices.
- Adaptive-minus-comparator uncertainty reuses the declared seven-calendar-day,
  circular paired station/time bootstrap with 2,000 resamples and fixed analysis
  seed. Preserve calendar gaps, average the recorded three seeds within stations,
  and share calendar draws across stations. Intervals are exploratory marginal,
  conditional on this small nonrandom/possibly colocated Development cohort and
  all staged tuning. They are not population, simultaneous or unbiased Final CIs.
- Saved old-policy audits provide descriptive paired new-minus-old gaps, with
  unscored audits remaining null. No harmful-switch threshold or recovery time is
  invented. Cost rows retain candidate/audit steps, elapsed totals and reset GPU
  peaks; reused Source/preparation/export and overlapping fixture/backup costs
  still need explicit total capacity accounting.

The collection records whether selected Fixed Retention lies in the Adaptive
candidate set. If it does not, surface this for ablation/fairness review rather
than silently changing the selected baseline or controller. Proxy signal-versus-
retention relationships, load-density context thresholds and complete fairness/
capacity review still need actual analysis. This command cannot grant Final lock,
independent peer approval, merge or acceptance of all Sprint 3 deliverables.

## Completed primary matched execution — 2026-10-26

The original Kaggle batch completed all **690/690 fresh matched reference and
comparator runs**, after all 1,104 proxy/parameter calibration runs. Downloaded
server logs record exit 0 for matched training (3,061.748 seconds), independent
daily verification (343.701 seconds) and the first collection analysis
(79.518 seconds). These are stage wall times, not standalone per-method costs.
The later context/proxy analysis ran at clean code `5fa321f`. All training stayed
at clean `54131cbb` on one visible Tesla T4; no laptop training or Final outcomes.

The complete downloaded matched matrix and daily proof authenticate **127,650
daily files**, 690 run identities/counts/chains and 330 null-metric cells. Bound
latest-state proofs cover all 1,104 calibration and 690 matched runs on Kaggle.
Local recomputation authenticates all five matrix/proof dependencies, the exact
finite choices,966 selected cells and every station-first MAE/RMSE point estimate.
This does not substitute for independently restoring daily files and checkpoint
contents outside Kaggle; full multipart transfer/restore is still underway.

Conditional Development MAE (kWh), with paired seeds 42/43/44 averaged within each
station, stations weighted equally within each budget:

| Method / unique variant | 7-day | 14-day | 28-day | Equal-budget mean |
|---|---:|---:|---:|---:|
| `adaptive` | 4.842021 | 5.098825 | 5.524448 | 5.155098 |
| `block28` | 4.860595 | 5.114370 | 5.529150 | 5.168038 |
| `block7` | 4.823624 | 5.074131 | 5.501052 | 5.132936 |
| `drift` | 4.889842 | 5.100598 | 5.508642 | 5.166361 |
| `fixed_retention` | 4.808104 | 5.056981 | 5.499802 | 5.121629 |
| `frozen_source` | 5.052220 | 5.250804 | 5.687057 | 5.330027 |
| `full_finetuning` | 4.899140 | 5.144953 | 5.527041 | 5.190378 |
| `online_best` | 4.905242 | 5.090410 | 5.517026 | 5.170893 |
| `parameter_retention` | 4.899126 | 5.144972 | 5.526255 | 5.190118 |
| `seasonal_naive` | 8.845463 | 8.463111 | 9.810850 | 9.039808 |
| `source_error` | 4.846813 | 5.097881 | 5.526969 | 5.157221 |
| `target_only` | 8.775013 | 8.023459 | 8.528936 | 8.442469 |
| `uncertainty` | 4.846813 | 5.120451 | 5.524383 | 5.163882 |
| `without_source_initialization` | 8.971036 | 8.261207 | 8.578580 | 8.603608 |

**Adaptive does not beat selected Fixed Retention on any of these three budget
point estimates.** It improves on Full Fine-tuning in this selected cohort;
that is not evidence of population superiority or a reason to keep searching
until a favorable configuration appears. No new tuning configurations were added.
The nonrandom cohort has only 3/4/5 scored IDs by budget; another 3/4/4 IDs remain
unscored. The complete selected 14-method collection retains 462 null cells out of
966, not zero errors. Budget IDs differ and possible co-location remains.

Fourteen unique methods cover the main method, nine baselines and five ablation
categories through declared aliases: Without Confidence reuses Online Best-lambda
at delta 0, and Fixed lambda reuses Fixed Retention. Selected Fixed lambda 1 lies
inside the Adaptive candidate set 0/0.1/1. Fresh Kaggle Adaptive/FT/Fixed rows
replace earlier Colab comparison rows; the old outcomes remain calibration
provenance only. All common runtime/config/input/Source identities match.

The downloaded context/proxy summary includes exploratory station/calendar
intervals, density/weekday/initialization/30-day slices, descriptive proxy
relationships and component costs. Complete off-runtime re-execution of those
joins/intervals and stronger full-collection audit/switch checks remains pending;
no equivalence, causal, independent Final or related-paper reproduction claim.
Independent review and complete compute/storage acceptance are still required.
CHARGED's six separate-city full replications have not started.

[Exact metrics, provenance and acceptance boundaries](issue23-matched-evidence.json)
· [metadata/proofs/analysis/logs ZIP](https://drive.google.com/file/d/1VTTbc30qxMbKA4oAdKcASiJMnqijkH5a/view).
The ZIP passed anonymous byte/hash/CRC and all member fingerprints. It is not a
full checkpoint/forecast backup. Complete exports are now generated on Kaggle
(94 calibration parts, 60 matched parts) and are being transferred without deleting
source runtime copies. No Final lock/evaluation, autonomous merge or issue closure.

Historical implementation status:269 fixture tests initially passed before the
full matrices completed. The current321-test implementation and subsequent
actual evidence do not imply independent peer approval. Earlier source/fixture
snapshots retain their original scopes; see the linked evidence record and
[analysis definitions](issue23-analysis-extensions.md).
