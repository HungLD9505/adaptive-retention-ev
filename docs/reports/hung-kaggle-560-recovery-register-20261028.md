# Kaggle 560-job archive recovery checklist — 28 October 2026

This [28-row checklist](hung-kaggle-560-recovery-register-20261028.csv) enumerates the Kaggle shards still missing local per-job archive bytes in the [second ledger audit](hung-development-782-ledger-audit-20261028-v2.md). Each row has 20 planned job IDs. The [generator](../../tools/hung_kaggle_recovery_register.py) checks the frozen partition SHA against the tracked allocation, hashes each shard's exact ordered jobset and compares it with the pinned queue jobset SHA. It requires 28 disjoint shards and 560 jobs.

The `saved_version`, `archive_bytes`, `archive_sha256` and ignored local archive path fields are deliberately blank. This checklist does **not** claim that the archive versions or per-job bytes were fetched. Saved provider readback reports remain separate aggregate evidence. Populate those fields only from the exact saved provider version and independently checked archive; then run the ledger's receipt/manifest/member checks into a new versioned snapshot. Do not treat an upload acknowledgement, source notebook, or planned jobset hash as an archive hash.

`python -X utf8 -m tools.hung_kaggle_recovery_register` exited 0 with 28 shards and 560 jobs. It byte-compares an existing CSV rather than overwriting it. No Kaggle job or download was started by this checklist.

The ledger verifier now has a **prepared**, optional `--recovery-manifest` route. For each downloaded archive, an ignored JSON manifest must provide `shard_id`, `planned_jobset_sha256`, positive `saved_version_id` and `readback_version_id`, `archive_path` under this worktree's ignored `.cache`, `archive_bytes` and `archive_sha256`. The verifier rejects non-Kaggle/duplicate shards and jobset mismatch before opening the archive; its existing per-job receipt/manifest/member checks then apply. The route requires `--out` naming a new CSV under `docs/reports`, preserving the 206- and 222-verified ledgers. This route has **not** verified any of the 560 missing jobs because no exact Kaggle archive bytes were retrieved here.

The version IDs in that ignored manifest are caller-supplied identifiers; this local verifier does not query Kaggle to authenticate them. Before assigning remote-readback status, compare each ID and archive fingerprint against the saved provider receipt/log independently. A successful local row means local byte/receipt/manifest verification only.

Once genuine archive files and version receipts are in place, create an ignored JSON file such as `.cache/recovered-shards-v3/manifest.json` with schema `hung-kaggle-archive-recovery-v1` and an `archives` array. Each entry needs the seven fields listed above; use the exact `planned_jobset_sha256` from the checklist and an archive path relative to the repository root. Then run:

```sh
python -X utf8 -m tools.hung_reconcile_782_snapshot_v2 --recovery-manifest .cache/recovered-shards-v3/manifest.json --out docs/reports/hung-development-782-job-ledger-20261028-v3.csv
```

The command fails on a missing or wrong-shard archive and never replaces either prior ledger. Do not create or publish the v3 CSV until at least one exact recovered archive has passed its receipt/member checks.
