# Hung E2E gate checkpoint — 28 October 2026, CPU export through batch05

This create-only checkpoint supersedes the time-bound [v8 register](hung-e2e-gate-register-20261028-v8.md) for CPU export status. Training remains reported executed for 782/782 distinct Development jobs. Export metrics and per-job archive proof have different acceptance gates.

| Gate | Current evidence | Remaining condition |
| --- | --- | --- |
| CPU export | [Batch04](hung-cpu-export-readback-04-20261028.md) and [batch05](hung-cpu-export-readback-05-20261028.md) were independently ingested with exact 80-job sets, saved bytes/SHA and passed receipts. Across batches00–05: **480/560** Kaggle jobs. | Batch06 is running; verify its saved 80-job output and ingest create-only before claiming 560/560. Recompute the full matrix and uncertainty after coverage closes. |
| Per-job proof | Published v4 ledger: **222/782** locally byte-verified. Corrected exact-stage verifier passed for 60 additional Kaggle jobs from saved archives, outside a new ledger snapshot. | Verify the other 500 Kaggle jobs, reconcile all 782 rows and obtain independent review. |
| Fairness and Final | Block7/parity/CHARGED decisions and Hùng-specific immutable Final lock are unresolved; no Hùng Final run. | Reviewer decision and Development acceptance before Final execution. |

No prior artifact was overwritten, no training was resubmitted, and no usage reset was used.
