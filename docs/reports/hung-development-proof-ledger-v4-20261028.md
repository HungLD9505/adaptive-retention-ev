# Development compact proof ledger checkpoint (28 October 2026)

## Result and acceptance state

The create-only [v4 ledger](hung-development-782-job-ledger-20261028-v4.csv) contains exactly 782 unique Development jobs:

| Status | Jobs | Meaning |
| --- | ---: | --- |
| `VERIFIED_LOCAL_BYTES` | 222 | Unchanged from frozen v2; archive/member bytes were checked locally. |
| `PROVISIONAL_REMOTE_COMPACT_PROOF` | 180 | Nine saved v1 compact proofs and three separate proof readback receipts were imported. Reviewer P1 prevents acceptance. |
| `MISSING_REVIEWABLE_ARCHIVE` | 380 | Nineteen Kaggle shards still lack imported per-job proof. |

The v4 ledger SHA-256 is `095b24adbef2fba28c430ce72d3f6c2f1d575e4e45a2f17efde7c629602c6826`. The 180 provisional jobs are exactly the 20 jobs in each of shards 0001–0003 and 0008–0013, with no duplicate job IDs. For each, the ledger records the frozen job identity, archive SHA/bytes, job receipt hash, stage manifest/receipt hashes, exact proof/readback bytes and SHA, and claimed saved version IDs. The readback JSONs bind proof bytes/SHA and ordered jobset SHA. The original archive bytes were not downloaded for this import.

Reviewer feedback on PR #72 identified a P1 false-accept case in compact verifier v1 when archive stages are empty. All 180 imported rows have nonempty stage hash maps, but that observation does not close the verifier defect. These rows remain **provisional** until a corrected verifier, fresh saved proof, and independent readback are reviewed. A local candidate v3 was generated before that feedback (SHA `18cdc7e2a7a42ffbff8914a5664bcc54e04ae471a1655dd5d682708b5994637b`); it was preserved in the isolated worktree but is superseded and **not committed as evidence**.

## Provenance

The [import manifest](evidence/hung-compact-proof-ledger-import-manifest-20261028-v1.json) pins every file byte count and SHA. The exact 12 JSON files plus their [transport manifest](evidence/hung-compact-proof-transport-363114949/transport-manifest.json) were decoded from a saved CPU log transport, version `363114949`; that transport checked contiguous chunks and raw byte/SHA before writing. Each proof is paired with its own entry in a single-shard or group readback JSON:

| Shards | Jobs | Proof version | Proof readback version | Archive carrier / readback version |
| --- | ---: | ---: | ---: | --- |
| 0001 | 20 | 363099687 | 363102461 | 362612528 / 362633606 |
| 0002–0003 | 40 | 363105577 | 363107432 | 362625674 / 362635685 |
| 0008–0013 | 120 | 363111778 | 363113838 | 362690241 / 362709067 |

For shards 0008–0012, carrier `362690241` is **not** their original training run. The original execution mapping in [HTTP499 recovery](hung-provider-499-recovery-20261027.md) and [CPU capacity recovery](hung-cpu-capacity-recovery-20261027.md) is: shard 0008 ran in GPU `362635685`, shards 0009–0012 in GPU `362649842`, and shard 0013 in GPU `362690241`. Earlier outputs were carried forward and independently read back by CPU `362709067`. All provider version IDs in the compact proof and import manifest remain claimed IDs, not independently authenticated by the local importer.

## Reproduction and checks

1. Copy the 12 exact JSONs from `docs/reports/evidence/hung-compact-proof-transport-363114949/` into ignored `.cache/compact-proof-transport-363114949/` without changing bytes. Copy the tracked import manifest into ignored `.cache/hung-compact-ledger-import-20261028-v3.json` without changing bytes.
2. Run `python tools/hung_import_compact_proof_ledger.py --manifest .cache/hung-compact-ledger-import-20261028-v3.json --out docs/reports/hung-development-782-job-ledger-20261028-v5.csv`. A new filename is required because output is create-only; compare its counts and rows to v4.
3. Run `python -m unittest tests.test_hung_import_compact_proof_ledger tests.test_hung_kaggle_compact_proof -v` and Ruff check/format for the importer and tests.

The importer checks frozen ledger/register/allocation/verifier pins, exact ordered shard jobsets, per-row identity, proof/readback byte/SHA, group completeness, and duplicates. It cannot authenticate saved Kaggle version IDs or fix verifier v1. Next, repair the verifier P1 case, generate fresh proofs/readbacks from saved archives, and import them into a new ledger snapshot; continue the remaining 19 shards and Development metrics/export work separately.
