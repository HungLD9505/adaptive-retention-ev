# Kaggle compact per-job proof: group03 recovery carrier

**Scope:** Development-only, six saved shards (`shard_0008`–`shard_0013`) containing 120 already trained jobs. No training or Final run was submitted by this proof. The proof and independent readback both used CPU accelerator `None`.

## Source binding and archive pins

The proof mounted the existing [group03 recovery saved output `362690241`](https://www.kaggle.com/code/hungluongduc/hung-group03-shard13-recovery-20261027-v1?scriptVersionId=362690241) and the private parent payload dataset v1 (`149,838,818` bytes; SHA-256 `23a6d420523d990d07ff07d814ed642a851925283a102a3ae806f3b666e1d6f4`). The recovery output carried previous shards 8–12 and executed only shard 13. The [previous independent CPU readback `362709067`](https://www.kaggle.com/code/hungluongduc/hung-g03-s13-readback-20261027-v2?scriptVersionId=362709067) exposed the six archive fingerprints below, each with CRC passed. Its saved input listed the exact recovery output version. The compact verifier independently checked each archive again, plus the frozen plan SHA `34f252fd19e33698a56faf4f3b19e921248ddf419b91fdfc3a69e7bc3f63f1a4` and partition SHA `3f022fe12fe9918062959240b8f1dd3be9b25f18fdcae982ba972f867e78c342`.

| Shard | Archive bytes | Archive SHA-256 | Compact proof bytes | Compact proof SHA-256 |
| --- | ---: | --- | ---: | --- |
| `shard_0008` | 74,362,442 | `a49fc9c6c56b5e6cdcf54bb1af15d05cb511d017f3be3cb4abfb41f17dc151e8` | 25,086 | `460ee5c8703ca6a35f7d4e1a06e038d93b5d8eecd5c3f8df7ad583ac0fcfbd38` |
| `shard_0009` | 68,786,447 | `37f635185da5bf08fd927e0ecacb9efb53f41f2b87f85ad3554f5a92ee53de5e` | 25,098 | `509f30f21455a65579a7a2d8e0083143747989495295d36d5f3272ca45f23f51` |
| `shard_0010` | 66,147,049 | `c83b3af82e5eedc2c4b68d0bb1d808b10e66fb037708bb5345c38ae3c602b180` | 25,044 | `6f03412c5386dd65d7c99bf8e7d67e2d9fa3a85b82454749146c48bf725b3a3f` |
| `shard_0011` | 317,485,131 | `959dbb76e407ac6c1ff7fce723fdc1510046280b1b473902ede231ff79bcfc6b` | 22,791 | `632d6531c2d53644a9a1ab7209f04c2067b9e0e6b76973cf3268b9bb0204309e` |
| `shard_0012` | 452,751,164 | `d0f7f0335745843adbf16b5c05aafd7fb7a4505ba13c92ab649849677d9b92dc` | 21,584 | `dcea62992dd8c65824739b69571727ad68db33a97d7022c8fde55c08c747ba9b` |
| `shard_0013` | 453,014,419 | `49442d6a54209957e2fc008f3f7891b5160c7a9e23fa7c5eee7c49f46f710b51` | 21,569 | `b43feb6603fd6f09f5202411da643c8fa306b7ae4c999edef3cce5e624b01a36` |

## Saved verification

[`hung-compact-proof-group03-20261028-v1`, version `363111778`](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-group03-20261028-v1?scriptVersionId=363111778) completed successfully in 105.9 seconds. Its saved output has six compact proof JSONs and four derivation files. The terminal log reported six `VERIFIED_ARCHIVE_BYTES` proofs, 20 unique rows each, with the exact proof byte counts and hashes above. A prior draft preflight produced the same six hashes. The submitted notebook source was Ruff fixed and formatted before saving; Ruff lint and format checks and AST parsing passed locally. The embedded verifier source hash remained `a7b6ebd0fbd69001e34b874fff0dba1c6d9ecc1e6dae682318a410074b537b90`.

[`hung-compact-proof-group03-readback-20261028-v1`, version `363113838`](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-group03-readback-20261028-v1?scriptVersionId=363113838) completed successfully in 9.2 seconds. Its saved input lists proof version `363111778`. It reopened all six proof files, independently recomputed exact bytes and SHA, checked 120 disjoint job IDs, the frozen ordered jobset SHA for each shard, archive fingerprints, and row statuses. It wrote one `REMOTE_PROOF_READBACK_VERIFIED` JSON receipt; its saved output lists one file.

The nine Kaggle shards proved so far (`0001`, `0002`, `0003`, `0008`–`0013`) total **180/560 remotely proofed and independently read back jobs**. The 120 per-job rows here remain in saved Kaggle proof JSONs until exact raw bytes are ingested into a local versioned 782-row ledger. Saved version IDs are caller claims inside the proof JSON; their separate Kaggle pages and source bindings were observed, while the source UI reported `isSourceIdPinned:false`. Peer review and Development acceptance remain pending.
