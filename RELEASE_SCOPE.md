# Main candidate: supervisor-report research snapshot

This release candidate consolidates the work in dev for the student research report.
It is not a claim of universal Adaptive superiority, complete dual-implementation
replication, calibrated future-switch safety, or a curated public dataset release.

| Include on main | Purpose and boundary |
|---|---|
| `ev_inputs`, `ev_models`, `ev_control`, `ev_runner`, `ev_baselines`, `ev_evaluation` | Primary 24→24 pipeline and analysis; original results belong to the frozen source, not later verifier revisions |
| `tools` and `configs` | Identified data/replay/verification utilities and frozen configs; historical operation tools are not instructions to resume production |
| `report` | Exact delivered report/supplement PDFs and source, figures and result tables; no new compile or numerical result is claimed |
| `experiments/member_studies` | Attributable isolated studies with their actual validation boundaries; not primary Final evidence |
| `experiments/hung_sprint2` | Separately identified supporting implementation and bounded three-station evidence; no pooled scores or full cross-city equivalence |
| `docs/data`, selected entry points and curated `docs/reports` | Contracts, final provenance, negative/null outcomes and verification dependencies; intermediate drafts are retained in the archive tag |
| Offline tests and explicit external-artifact tests | Keep fixture checks distinct from checks that require original trained artifacts |

Do not include raw archives, processed/input datasets, environments, checkpoints,
large runs, temporary manuscript builds or local operational state in Git. They stay
in ignored storage with recorded hashes. Superseded branches remain in SHA-pinned
archive tags; they are not additional active implementations to run.

## Scope limits retained for this report

- **#23:** Primary 810-unit/11,340-cell Final and analysis are complete. Missing full
  end-to-end timing/memory/billing information cannot be recovered from update counts;
  lost compute and incomplete timing remain unknown. No new training is planned to
  replace those observations. The original unrestricted accounting acceptance is
  retired as **not planned**, rather than declared experimentally satisfied.
- **#39:** Hùng's bounded 360-job supporting result is retained. The earlier expanded
  full dual-E2E/cross-city/reproduction assignment is not complete and is not needed
  to label the primary report's actual scope. That expansion is **not planned** for
  this release; disputed physical lineage and incomplete private-artifact reproduction
  remain explicit limits, not approved replications.
- **#40:** Đức's bounded CPU study and recorded 152 artifact/49 checkpoint checks are
  preserved. The reported 23,035,669-byte bundle has no verified distribution link in
  this release. That unresolved handoff is **not planned** here; successful Drive
  upload/access is not invented. No training is repeated.
- **#41:** Cyber's historical results stay separate from the corrected IO code.
  Fixtures validate the new guards; they do not create corrected real-data results.
  New training/validation is **not planned** here, and the old result is not relabeled.
- **#15:** Remains the release decision gate until the exact candidate is chosen for
  main and the final handoff is actually made. Closing research-scope tickets as
  not planned does not close that release gate or assert its November 6 goal achieved.

The human lead requested no additional training and waived paid-CI waiting/non-author
review for repository integration. These are recorded lead exceptions, not independent
scientific approval or remote CI success. Any later training, method change or scope
extension requires its own versioned experiment; it cannot rewrite the frozen evidence.

## Reproduction identity

Original scientific source: `evidence/primary-final-20261027-v2` at
`61c32328d9829a69037dca629f727b4863015122`. All 92 tracked pins match that source.
Current verifier/metadata hardening is versioned separately and does not alter old
run bytes, expected hashes, cohorts, seeds, model or loss. No new broad performance
or equivalence claim follows from source integration.

Run `python -m tools.check_release` for an offline package/provenance check. It checks
report bytes, source-head reachability, original tracked source and excluded tracked
storage paths. It does not download data, train, verify missing remote artifacts,
compile PDFs or certify GitHub's contributor UI. The original export remains the
last actual PDF compile/layout check.
