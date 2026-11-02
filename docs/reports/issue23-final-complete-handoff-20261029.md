# Issue23 Final execution and analysis handoff — 2026-10-29

The authorized frozen Final execution is complete: **810/810 whole units and 11,340/11,340 method cells** are canonical. All seven namespaces have completed the unchanged original analyzer, independent output arithmetic review, and independent derived-CSV bootstrap review. All provider GPU sessions have ended. This is an execution and analysis handoff, not a claim of scientific superiority, human peer approval, passing CI, or authorization to merge or update `main`.

## Canonical evidence and reproducibility

The final ledger is [`progress-ledger-v813.json`](../../runs/issue23-final-execution-20261027-v1/progress-ledger-v813.json), SHA256 `1be8a84c6ce0097492ee9dd6e2a2f8e0eae3e745dc5f7b94a47e603aa6b85a02`. Its accepted indices are exactly 0–809, with 810 distinct canonical receipt bindings. Historical ledger fields describing old workers, reserve balances, or deployment status are not current observations.

The complete [artifact manifest](../../runs/issue23-final-analysis-20261028-root-v1/full-final-handoff-artifact-manifest-v1.json), SHA256 `3bf603066cfc0caf6064cab74ca6f4ade3d02b8aba29874c0b227ff1700fd0d2`, records each namespace's analyzer manifest, output file sizes and SHA256 values, independent review files, coverage, null retention, and terminal/recovery evidence. These operational artifacts remain outside Git; preserve them with the existing run archive and canonical Drive publications. The ledger retains the per-unit publication and receipt references. This handoff does not assert that a new external backup of every local analysis file has been created.

Production science remains commit `61c32328d9829a69037dca629f727b4863015122`; execution lock SHA256 `9c65169cced1506a450fdd7b8a57a69d5a720cac7acaa0dcd1c8ccfd1723ce42`. The frozen scope retains 90 entities, history budgets 7/14/28 days, paired seeds 42/43/44, all 14 methods, 90 scheduled evaluation days, 140 scientific file pins, 721 runtime packages, and 21 original Source artifacts. No cohort substitution, method tuning, city pooling, label filling, raw archive overwrite, or blind refit was performed for this handoff.

The original analyzer SHA256 is `25dd23f8172bd9d4952b6530ab8978c6735031c65f34db3c9d670a1428251325`. Analysis used `/tmp/ev-issue19-env/bin/python`; this CPU analysis runtime is distinct from the recorded Python 3.13/Tesla T4 production runtime. Analyzer manifests retain their actual code/runtime provenance; these identities are not relabeled as the production environment.

## Completed namespace analysis

| Namespace | Whole units | Method cells / daily-latest proofs | Independent bootstrap comparisons | Null method cells | Null bootstrap intervals |
| --- | ---: | ---: | ---: | ---: | ---: |
| UrbanEV / SZH | 270 | 3,780 | 42 | 126 | 42 |
| CHARGED / AMS | 90 | 1,260 | 42 | 0 | 0 |
| CHARGED / JHB | 90 | 1,260 | 42 | 0 | 0 |
| CHARGED / LOA | 90 | 1,260 | 42 | 0 | 0 |
| CHARGED / MEL | 90 | 1,260 | 42 | 0 | 0 |
| CHARGED / SPO | 90 | 1,260 | 42 | 0 | 0 |
| CHARGED / SZH | 90 | 1,260 | 42 | 0 | 0 |
| Total | 810 | 11,340 | 294 | 126 | 42 |

Per-namespace `summary.json` contains the frozen station-first metrics, all methods and comparators, budget-specific results, context/initialization/density strata, transfer signs, bootstrap estimates, and recorded cost caveats. `runs.csv` retains per-cell metrics; `independent-daily.json` contains the original analyzer's daily/latest-state proofs. Their exact paths and hashes are in the artifact manifest. No cross-city pooled effectiveness estimate is introduced here.

All seven independent output reviews report no discrepancy in audited arithmetic. All seven independent bootstrap reviews report `MATCHES_FROZEN_REPORTED_BOOTSTRAP`, with zero maximum absolute scalar difference. Across 294 comparisons, the 252 defined intervals contribute 504 numeric endpoints; Urban's 42 null intervals remain null.

The final SZH analyzer was actual command session 5792, exit 0, with 1,260 daily/latest proofs. Its output review passed 11,103 checks and 4,200 numeric comparisons; maximum absolute arithmetic difference was `4.547473508864641e-13`, within the existing tolerance. Export session 91196 exited 0 with 113,400 scored daily rows and no null method cells. Independent bootstrap session 82914 exited 0: all 42 comparisons matched, no discrepancies, no undefined replicates, and no null intervals. These are completed runs, not fixture-only results.

Urban entity 2193 remains unscored: all 126 associated method cells are retained as null. The frozen bootstrap produces 40 undefined replicates out of 2,000 in each of its 42 comparisons. Under the unchanged rule, every corresponding interval remains null, including the adaptive self-comparison whose point estimate is zero. No undefined replicate was dropped, filled, or converted into a finite interval.

The independent bootstrap uses the separately implemented frozen code, SHA256 `d9d07327f0db6e3f8f271c0ebbc894df51e59b87aaab38abf6d8974d4c541a1c`, with station-first weighting, budget-matched pairing, the shared 90-day calendar, seven-day blocks, 2,000 resamples, seed 20261026, and alpha 0.05. Root executed the separately implemented C audit code for MEL/SPO/SZH with documented city-literal adaptations and unchanged bootstrap core. This is not a separate C-agent execution or human peer review. Previously accepted artifact verification and completed analyses were not rerun to obtain the handoff.

## Execution provenance

The [original execution and terminal-state record](https://github.com/HungLD9505/adaptive-retention-ev/blob/c8a2afc007bb6e8f739dec219d43ae06f492139c/docs/reports/issue23-final-complete-handoff-20261029.md) preserves operational process/session identities.
These historical identities are provenance, not instructions to restart workers.

## Interpretation and remaining review boundaries

The original analyzer's daily/latest checks and the separate derived-output audits have different scopes. The latter validate reported arithmetic, pairing, and bootstrap reconstruction from the exported derived inputs. They do not independently rederive raw forecast errors, revalidate all model/checkpoint/raw-input archives, establish full provider billing, or prove novelty or effectiveness.

Results are conditional on the frozen, nonrandom selected cohort and paired seeds. Retain all adverse outcomes and missing values, the small/possibly colocated station caveat, calendar/bootstrap assumptions, exploratory marginal intervals without simultaneous-comparison correction, and the separate SZH temporal-overlap scope. SPO's ten metadata-ready IDs form its stated census; they are not ten independent geographic replicates. No population-wide, causal, or pooled-city superiority inference follows from execution completion.

Source cost is reused separately once; missing predecessor costs, setup/publication overlap, lost D compute, runtime differences, and GPU timing/peak caveats prevent a complete billing or fair speedup claim. The explicit peer-review exception and CI billing waiver do not constitute peer approval or passing CI. No merge, `main` promotion, or issue closure is authorized by this report.

Validation for this handoff comprised actual analyzer/audit exit codes, complete ledger/index/receipt consistency, reconciliation of all seven output manifests against current file bytes and hashes, exact null/undefined retention checks, and actual provider termination evidence. Full README/CI checks were not rerun for this documentation and operational-evidence handoff; no passing-CI claim is made. The tracked change is this report; scientific code and expected fixtures remain unchanged.
