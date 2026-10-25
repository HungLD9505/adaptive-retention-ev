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

## Current status

269 fixture tests pass locally; lint/format and diff checks pass. Actual full-
collection analysis has not run because upstream GPU matrices remain incomplete.
The CLI will be staged for remote tests and execution only after all five real
matrices have independently passed verification. Its output is a fresh directory
with `summary.json` (selections, lineage, metrics, intervals, strata, audits and
costs) and `runs.csv` (all selected cells, including nulls). Reports will link
actual artifacts only after completion and independent verification.
