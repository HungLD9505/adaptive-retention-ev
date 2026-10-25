# Issue #23 — core-transfer comparator extension

## Pre-execution declaration, 2026-10-26

Add Full Fine-tuning (lambda0), Fixed Retention (lambda0.01), and Online Best-lambda
to the identified138-run UrbanEV readiness experiment. This adds207 runs, not207
independent station samples. Keep all23 entity-budget combinations, seeds42/43/44,
90 scheduled days, missing/null units and identified Source weights. No selection
based on the newly observed comparator outcomes. Diagnostic settings remain
unchanged; this is not completed tuning, a full baseline matrix or a Final lock.

Reference matrix SHA-256:
`f94f4ed5eab3f9a3b47259aacff3c200668ba7ffe30f5249957575d3ce0d6b29`.
Cohort SHA-256:
`6884857291b79b35f83cc7d78b6fc7a2b5fe0283ebe85c0321a5eb1a5ee283f0`.
Source-pool matrix SHA-256:
`a1a8ec96074402564671e952c184e499eb4e30aa8f9e7b10a4e0cfe0a5e7566e`.

`tools.development_comparators` inherits each paired reference run's exact config,
changing only the method definition. It rejects changed algorithm-module hashes,
input/Source/cohort identities, mismatched paired configs and missing/duplicate
reference cells. The original Adaptive and Target-only runs remain immutable and
are reused as references, not rerun for more favorable results. New outputs use
the declared latest-state persistence mode; per-run logs, failures, metrics, bound
configs, code identity and daily forecast/event/state chains are retained.

The comparison can assess the diagnostic transfer/retention/confidence differences
under these settings, with the same daily score population. It cannot establish
optimal fixed retention, calibrated proxies, population superiority, or a matched
winner against Hung's different topology/configuration. Core comparison metrics
must keep source-only initialization and zero-score strata explicit.

Execution status: declared, not yet executed at this commit. Actual Colab results,
verification and artifact links will be appended after completion. No local real-data
training, Final forecast/label access, merge or issue closure is authorized here.
