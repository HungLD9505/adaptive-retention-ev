# Compact proof ledger import (prepared)

The frozen Development v2 ledger has 782 jobs: 222 `VERIFIED_LOCAL_BYTES` and 560 `MISSING_REVIEWABLE_ARCHIVE`. `tools/hung_import_compact_proof_ledger.py` creates a new 782-row snapshot after actual saved Kaggle compact proof JSON and separate CPU readback JSON have been copied into this repository's ignored `.cache/` directory. This document describes the importer; it does not claim that any remote proof was imported.

## Required input

Save each exact `hung-kaggle-compact-shard-proof-v1` JSON and its corresponding `hung-kaggle-compact-proof-readback-v1` or `hung-kaggle-compact-proof-group-readback-v1` JSON as distinct files under `.cache/`. Keep original bytes. Create a JSON manifest under `.cache/` with this shape:

```json
{
  "schema": "hung-compact-ledger-import-v1",
  "entries": [
    {
      "shard_id": "shard_0001",
      "provider_plan_sha256": "<64 lowercase hex digits>",
      "provider_partition_sha256": "<64 lowercase hex digits>",
      "archive_sha256": "<64 lowercase hex digits>",
      "archive_bytes": 1,
      "training_version_id": 1,
      "archive_readback_version_id": 1,
      "proof_version_id": 1,
      "proof_readback_version_id": 1,
      "proof_source_notebook": "<exact Kaggle notebook slug in readback JSON>",
      "proof_path": ".cache/<exact saved proof file>.json",
      "proof_bytes": 1,
      "proof_sha256": "<64 lowercase hex digits>",
      "proof_readback_path": ".cache/<exact saved readback file>.json",
      "proof_readback_bytes": 1,
      "proof_readback_sha256": "<64 lowercase hex digits>"
    }
  ]
}
```

Replace every placeholder with observed values. A group readback requires entries for every shard it covers. Each compact proof must have its own independent readback entry; a proof alone cannot mark any job verified. Submit only shards with both exact JSON files available. The importer retains all other jobs as pending. An empty manifest is rejected.

Run from the repository root, choosing a **new** v3 or later filename:

```powershell
python tools/hung_import_compact_proof_ledger.py --manifest .cache/compact-proof-import.json --out docs/reports/hung-development-782-job-ledger-20261028-v3.csv
```

The command checks the frozen v2 ledger, recovery register, allocation evidence, and verifier source hashes; exact 20-job shard membership and order; model/plan/config/input identity; archive and receipt hashes recorded by the saved verifier; proof bytes/SHA; independent readback bytes/SHA and status; and duplicate jobs/shards. It writes with create-only mode and never changes the v1/v2 ledgers. `VERIFIED_REMOTE_COMPACT_PROOF` means the saved CPU verifier checked archive bytes/SHA/CRC and receipts and another saved CPU run checked the compact proof bytes/SHA. It is distinct from `VERIFIED_LOCAL_BYTES`. The importer does **not** independently authenticate Kaggle version IDs or reopen the original archives locally, so those version IDs remain labeled claims.

For the four frozen tracked text inputs, the SHA pins refer to Git's LF byte content. Git may check those files out with CRLF on Windows. The importer converts CRLF to LF in memory only for those pin checks, rejects any bare CR, and never rewrites the files. Proof and readback JSON retain exact byte/SHA checks without newline conversion.

After all 28 shard proofs and readbacks are imported, check that the generated summary reports 782 rows, 222 local-byte verified, 560 remote-compact-proof verified, and zero pending. Keep the manifest and imported JSON copies for review. Do not call Development complete until all 28 real shards meet these checks and the broader metrics/export/review gates are satisfied.
