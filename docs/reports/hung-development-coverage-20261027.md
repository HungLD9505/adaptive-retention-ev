# Development matrix coverage audit — 2026-10-27

This read-only audit reverified 171 local/historical artifacts against their manifests, checkpoints and supporting receipts, then counted logical cells separately from physical artifacts. It does not approve a Final lock or read Final labels.

Nine baseline families and five ablation categories are declared across 69 station/budget/seed cells: budgets 7/14/28 and seeds7/11/19. The immutable plan schedules 782 new jobs, alongside 69 historical Main reuse and 69 historical unmatched Block-7 runs. No accepted model/data/Source/Target contract or historical identity changed.

| Comparison | Required logical cells | Matched metric cells | Scorable cells | Unique artifacts | Unmatched cells |
|---|---:|---:|---:|---:|---:|
| main | 69 | 69 | 36 | 69 | 0 |
| seasonal_naive | 69 | 36 | 21 | 12 | 0 |
| target_only | 69 | 1 | 1 | 1 | 0 |
| frozen_source | 69 | 1 | 1 | 1 | 0 |
| full_finetuning | 69 | 0 | 0 | 0 | 0 |
| fixed_retention | 69 | 0 | 0 | 0 | 0 |
| online_best | 69 | 1 | 1 | 1 | 0 |
| source_error | 69 | 29 | 13 | 29 | 0 |
| uncertainty | 69 | 57 | 29 | 57 | 0 |
| drift | 69 | 0 | 0 | 0 | 0 |
| without_confidence | 69 | 1 | 1 | 1 | 0 |
| fixed_lambda | 69 | 0 | 0 | 0 | 0 |
| parameter_retention | 69 | 1 | 1 | 1 | 0 |
| block7 | 69 | 0 | 0 | 0 | 69 |
| block28 | 69 | 0 | 0 | 0 | 0 |
| no_source | 69 | 0 | 0 | 0 | 0 |

The columns describe the authenticated metric catalog, not the live execution ledger. Some executed Kaggle jobs are not yet imported into this metric catalog. Zero scored horizons remain missing observations, not zero errors. Different comparisons can have different label coverage; this table neither ranks methods nor selects configurations.

Without Confidence reuses Online Best-λ only for the exact otherwise-identical pinned configurations with δ=0. The CLI verifies that identity and the expected selection-rule difference. Fixed λ reuses Fixed Retention. Seasonal Naive maps its deterministic forecast to three seed views without counting three independent runs; each mapping requires the same budget/station/input hash and no model initialization. Other model-dependent seeds remain distinct. These are declared reuse mappings, not extra training results.

Different Block Size includes both planned 7-day and28-day variants. All 69 historical Block-7 cells remain unmatched, regardless of previously observed payload equivalence. Independent fairness disposition is still required; this audit refuses to promote those IDs merely because a new catalog labels them verified. Full matched family/cell coverage is **not achieved**.

The audit binds the canonical plan through the original derivation to the generator coverage: parent/derived SHA, exact jobs/cells/cohorts/seeds/selection/input base, and unchanged config hashes. It requires complete seed cohorts, rejects duplicate/foreign/unverified artifacts and changed aliases, and verifies all saved metrics through the existing scorer before counting them. The raw catalog has 171 unique physical artifacts. Aliased views never increase that count.

Model code remains `44b8532959d76fb20691881539f991ca44983727`. Canonical plan SHA remains `2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee`. The evidence JSON records every config hash, budget-specific input hashes, Source/Target checkpoint hashes, raw audit/log/spec pins, per-budget counts and missing/unmatched cell IDs. The actual CPU audit exited 0 in 26.340 seconds.

The clean-commit full suite passed **332 tests, one skip, exit 0**, at `f383903`. Ran 332 tests in 211.619s. Wrapper time was 218.582 seconds. Full Ruff lint/format (123 files) and diff checks passed. Seven new tests cover alias accounting, unmatched rejection, missing metrics, zero-scored observations, changed alias inputs/initializers, duplicate/missing seed evidence and rejection of Final scope. The actual 171-artifact audit also exited 0. [Machine-readable evidence](evidence/hung-development-coverage-20261027.json) preserves all input/output and terminal pins.

The remaining Final gates include accepted data/provider scope, independent fairness/scientific review, reviewed label coverage/exclusions, station/time uncertainty, context and seed stability, switching/isolated audit analysis, an immutable configuration/cohort/code lock, and measured Final capacity/storage. Successful job execution or a green coverage table alone cannot supply those approvals. No Final run, merge, issue closure or main promotion occurred. #39 remains open pending a non-author provider-substitution decision. `docs/SPRINT_PLAN.md` remains the only schedule.

Changed files: `tools/hung_coverage.py`, `tests/test_hung_coverage.py`, this report and its JSON evidence. Commands: focused coverage tests; full offline suite; full Ruff lint/format; `git diff --check`; `python -m tools.hung_coverage --spec ... --spec-sha256 ... --project-root ... --output ...`. Existing data, checkpoints and reports were preserved.
