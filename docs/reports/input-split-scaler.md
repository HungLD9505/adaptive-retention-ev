# Issue #18 — fixture-only split / scaler handoff

## Scope and status

Implements two small pure helpers and exact target-prefix bound arithmetic against the proposed Input Contract at `c406ae07606ca48859cf93f8b24dfffab79c7803`. The [policy and rationale](../data/SPLIT_SCALER_POLICY.md) specify algorithms, examples, review choices, failure cases and caller responsibilities. User authorization covers this next slice while earlier PRs remain open. This is implementation ready for review, not accepted research/input artifacts or completion of #18.

- Split: stable SHA-256 of namespaced string identity plus explicit salt; approximate 60/20/20 thresholds. No dependency on activity, input ordering or other cohort members.
- Scaler: linear p95 from an explicitly bounded, valid and available single-entity prefix; genuine zeros included; 1 kWh fallback only when p95 is zero; empty population fails.
- Prefix arithmetic: exact integer 7/14/28 nominal days. No windows, loader, training, source cutoff defaults or automatic target eligibility decisions.

The branch starts from `dev` at `62c7e2aa3dfe89014d22dd7813cd8f5ea32b512e`. It does not copy unmerged feature code or producer modules; combined PR integration remains outstanding. The shared package initializer matches PR #31. Review proposed normalization and allocation choices before official use.

## Verification

The committed evidence JSON records the code revision, file hashes, Python runtime, fixture run identity, elapsed time and actual unittest results. Reproduce with the README commands using Python 3.12:

```sh
python -m tools.sources list
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
git diff --check
```

New fixtures cover deterministic assignment and identity encoding, order independence, exact budgets, linear quantile, inverse units, no clipping, suffix/pre-prefix isolation, exclusive cutoff, delayed labels, genuine zero, sparse zero-p95, missing/empty populations, malformed values, duplicate bins, clock/boundary failures and fit fingerprint scope. They exercise local helpers, not a complete forecasting pipeline. Raw archives were not read or freshly verified; source listing reads catalog metadata only.

## Remaining work and risks

All proposed algorithm choices require peer review. No official salt, split IDs or eligibility counts have been selected. Identifier roles do not guarantee physically disjoint locations; zero-p95 fallback may yield large scaled values; undefined prefixes may make some targets infeasible. These risks are not waived. The loader must verify producer clock, row ownership, role-specific cutoff, exact prefix and availability policy; the helper cannot establish them from energy alone.

Next #18 slice: implement 24→24 windows and predictor/label separation on fixtures, with complete-label gates and prefix/boundary tests. Then integrate reviewed #16/#17/#30/#31 and this slice, run full checks, produce new identified real-data artifacts and report actual sample counts per city/budget. Do not hand off #19 or close #18 before those gates pass. No automatic merge, dataset changes or method changes were performed.
