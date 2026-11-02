# Hùng E2E gate register v17 — 28 October 2026

This create-only checkpoint supersedes [v16](hung-e2e-gate-register-20261028-v16.md) for the new Block7 availability, parity fixture and CHARGED lineage audits. The v16 Development counts and [#10 draft v2](hung-e2e-research-report-draft-20261028-v2.md) remain the technical baseline; this page records the additional evidence and still-open decisions. No scientific reviewer approval or Hùng Final lock is inferred.

## Development terminal technical accounting

The [v5 ledger](hung-development-782-job-ledger-20261028-v5.csv) technically verifies 782/782 new jobs, including 560/560 Kaggle exact-stage archive/receipt/manifest SHA/CRC readbacks; CPU metric export is 560/560. The [851-run analysis](hung-development-audit-20261028-v2/report.md) includes 69 separate historical Main anchors and identifies 444 scorable runs, 407 zero-scored runs in 11 station × budget cells, 816 valid and 748 blocked paired cells, 72 paired uncertainty/NTR groups, bounded switching and observed cost. The saved evidence does not explain why labels are absent. There is no Development training or Kaggle export batch left to resubmit.

## Scientific decisions requiring a non-author reviewer

| Gate | New bounded evidence | Still required |
| --- | --- | --- |
| Block7 historical mapping | [Checkpoint availability audit](hung-block7-payload-availability-20261028.md) SHA-streamed 508 direct `.pt` files and 22,711 `.pt` ZIP members in this repository. Exact historical Block7 Source/Target file hashes were absent (0/9, 0/69), while the Main files were present (9/9, 69/69). This does not refute the earlier payload-equality assertion. | Reviewer must inspect historical checkpoint bytes or a byte-pinned pairwise payload proof plus per-origin numeric tolerance, then accept the mapping or explicitly require 69 new replay IDs. `PENDING_PEER`; do not replay merely because evidence is incomplete. |
| Hùng–Qyroven parity | [Common synthetic trace](hung-q-common-trace-20261028-v1.md) pins Qyroven code and identical two-origin inputs. Event chronology agrees after normalization and initial GRU encoder difference is zero, but the first forecast differs by up to 0.253471732 normalized units and post-update encoder by 0.001999997. Both keep λ=0.1 under Bmin 2. | Correctness-based head and bootstrap/quantile contract, then a common **real Development input** event/gradient/optimizer/checkpoint-resume trace with declared tolerance. The synthetic keep fixture does not settle the known marginal-switch discrepancy. `PENDING_CONTRACT_AND_TRACE`. |
| CHARGED attribution/scope | [Lineage metadata audit](hung-charged-lineage-audit-20261028-v1.md) finds 18/18 matching input-manifest hashes between PR #67 and PR #52 and 172 overlapping `run_id` strings among 2,268 supplementary rows. The overlap is naming evidence, not proof of identical physical artifacts. | Exact run→executor/remote version/archive/receipt/Source/Target/config/code mapping, relationship to #52, physical SZH overlap rule and per-city accepted/limited/supplementary disposition. Preserve AMS adverse results. `PENDING_ATTRIBUTION_AND_SCOPE`. |

The [review dossier](hung-scientific-gates-review-dossier-20261028-v2.md) gives the decision form. The Qyroven `CHANGES_REQUESTED` review on PR #72 predates the corrected verifier and has no later submitted approval. At checked head `8a4a515`, both GitHub CI jobs failed before starting with the account payment/spending-limit annotation; no code assertion ran in CI. A latest-head independent review and CI clearance are still required for PR acceptance.

## Final and report gate

The [Final preflight](hung-final-runtime-preflight-20261028.md) found no distinct Hùng Final runner/dispatch or approved immutable lock. Hùng Final must wait for the three decisions, exact code/config/cohort/seed/threshold/analysis identities, a non-author #15 lock review, fixture-checked create-only runner, and a fresh capacity plan. The last local D-drive measurement was about 3.73 GiB free, below the existing Development dispatch 8 GiB reserve; measure again for the selected Final location. Run Hùng Final once under the approved lock, independently read back all output, then finish the E2E Results, Discussion and Conclusion. Qyroven's #23 exception does not authorize Hùng Final.

The Kaggle 20-minute monitor remains paused after technical completion. No Final/test input, training rerun, old-output overwrite or usage reset was used for these audits.
