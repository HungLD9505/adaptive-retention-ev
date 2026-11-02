# Hung E2E acceptance register — 28 October 2026, second update

This additive register supersedes the status counts in the [first register](hung-e2e-gate-register-20261028-v2.md) and retains its issue links, proof provenance, reviewer requests and limitations. `Verified` applies only to the named evidence; it is not issue or Final acceptance.

| Gate | Current evidence and disposition |
| --- | --- |
| #23 Development job evidence | [Second 782-row ledger](hung-development-782-job-ledger-20261028-v2.csv) and [audit](hung-development-782-ledger-audit-20261028-v2.md): **222/782** local archive/receipt/manifest/member byte-verified, **560/782** Kaggle archive bytes still unavailable to the local per-job audit. No duplicate or invalid planned job ID. Saved provider reports separately state 782/782 execution and remote archive readback. Local shard0039 is now included in the byte audit, but its remote readback remains pending. |
| #23 metrics/export | 371 Hybrid v4 physical runs, 196 scorable; authenticated batch00 covers 80 jobs. Batch01–06 terminal receipts and full paired metrics/uncertainty remain pending. Reader21 and coordinator06 were previously observed running; that observation is time-bound, not a current terminal status. |
| #22/#23 CHARGED | PR #67 publishes 2,268 supplementary Development proof runs. The [bounded descriptive summary](hung-charged-supplementary-proof-summary-20261028.md) includes all six cities and adverse results. Remote executor attribution, dependency and scientific acceptance remain pending. |
| #22/#39 fairness and parity | Block7's 69 historical runs await a cell equivalence decision or new replay IDs. Hung–Qyroven head, bootstrap and runner parity need an agreed contract and independent trace. |
| #39 Colab CUDA | Saved notebook proof states 63/63 stages. Immutable numeric export, independent Drive-byte readback, reviewer access and decision remain pending. |
| #23 Hung Final | No Hung-specific approved lock or Final execution. Proposed 90-ID scope remains a proposal; Development and review gates precede execution. |
| #10 E2E report | Development checkpoint and partial analyses are on draft PR #72. Full Results, Discussion and Conclusion require verified metrics and Final. Latest-head peer review and CI are pending. |

No Final outcome or 782/782 per-job verification is claimed. The first 206-row verified snapshot is retained for comparison; this update adds only the recovered shard0039 evidence.
