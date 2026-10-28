# Compact proof ledger import (prepared)

The frozen Development v2 ledger has 782 jobs: 222 `VERIFIED_LOCAL_BYTES` and 560 `MISSING_REVIEWABLE_ARCHIVE`. `tools/hung_import_compact_proof_ledger.py` creates a new 782-row snapshot after actual saved Kaggle compact proof JSON and separate CPU readback JSON have been copied into this repository's ignored `.cache/` directory. The v1 verifier has a reviewer-identified P1 empty-stage false-accept risk, so imported v1 proofs receive `PROVISIONAL_REMOTE_COMPACT_PROOF` until a corrected verifier and new proof are reviewed.

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
      "archive_carrier_version_id": 1,
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

`archive_carrier_version_id` is the saved Kaggle version from which the verifier opened the archive. For shards 0008–0012 this is a later carrier output, not their original training run. Keep the original execution version mapping in a separate provenance report; do not mislabel the carrier as training.

Run from the repository root, choosing a **new** v3 or later filename:

```powershell
python tools/hung_import_compact_proof_ledger.py --manifest .cache/compact-proof-import.json --out docs/reports/hung-development-782-job-ledger-20261028-v4.csv
```

The command checks the frozen v2 ledger, recovery register, allocation evidence, and verifier source hashes; exact 20-job shard membership and order; model/plan/config/input identity; archive and receipt hashes recorded by the saved verifier; proof bytes/SHA; independent readback bytes/SHA and status; and duplicate jobs/shards. It writes with create-only mode and never changes the v1/v2 ledgers. `PROVISIONAL_REMOTE_COMPACT_PROOF` means v1 proof bytes and readback were bound to the ledger; it is **not** scientific or archive-byte acceptance. The importer does **not** independently authenticate Kaggle version IDs or reopen the original archives locally, so those version IDs remain labeled claims.

For the four frozen tracked text inputs, the SHA pins refer to Git's LF byte content. Git may check those files out with CRLF on Windows. The importer converts CRLF to LF in memory only for those pin checks, rejects any bare CR, and never rewrites the files. Proof and readback JSON retain exact byte/SHA checks without newline conversion.

After all 28 corrected shard proofs and readbacks are imported and reviewed, check that a new accepted ledger reports 782 verified jobs. The v1 importer keeps these 180 currently available jobs provisional. Keep the manifest and imported JSON copies for review. Do not call Development complete until corrected proof, metrics/export, and broader review gates are satisfied.
