# Kaggle 560-job archive recovery checklist — 28 October 2026

This [28-row checklist](hung-kaggle-560-recovery-register-20261028.csv) enumerates the Kaggle shards still missing local per-job archive bytes in the [second ledger audit](hung-development-782-ledger-audit-20261028-v2.md). Each row has 20 planned job IDs. The [generator](../../tools/hung_kaggle_recovery_register.py) checks the frozen partition SHA against the tracked allocation, hashes each shard's exact ordered jobset and compares it with the pinned queue jobset SHA. It requires 28 disjoint shards and 560 jobs.

The `saved_version`, `archive_bytes`, `archive_sha256` and ignored local archive path fields are deliberately blank. This checklist does **not** claim that the archive versions or per-job bytes were fetched. Saved provider readback reports remain separate aggregate evidence. Populate those fields only from the exact saved provider version and independently checked archive; then run the ledger's receipt/manifest/member checks into a new versioned snapshot. Do not treat an upload acknowledgement, source notebook, or planned jobset hash as an archive hash.

`python -X utf8 -m tools.hung_kaggle_recovery_register` exited 0 with 28 shards and 560 jobs. It byte-compares an existing CSV rather than overwriting it. No Kaggle job or download was started by this checklist.
