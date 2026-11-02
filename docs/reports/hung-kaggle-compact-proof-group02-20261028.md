# Kaggle compact per-job proof: group02

**Scope:** Development-only, 40 already trained jobs across `shard_0002` and `shard_0003`. Both proof and readback were CPU runs with accelerator `None`; neither reran training.

## Immutable sources and checks

| Item | Saved identity or fingerprint |
| --- | --- |
| Training source | [`hung-matched-group02-44b8532-20261027`, version `362625674`](https://www.kaggle.com/code/hungluongduc/hung-matched-group02-44b8532-20261027?scriptVersionId=362625674) |
| Existing archive readback | [`hung-matched-group03-44b8532-20261027-v2`, version `362635685`](https://www.kaggle.com/code/hungluongduc/hung-matched-group03-44b8532-20261027-v2?scriptVersionId=362635685), whose saved input lists group02 output |
| Parent payload | Private `hung-matched-payload-44b8532-20261027-v1`, dataset version 1; `149,838,818` bytes; SHA-256 `23a6d420523d990d07ff07d814ed642a851925283a102a3ae806f3b666e1d6f4` |
| Derived provider plan / partition | SHA-256 `70dff1c41380aa781062470b6986829e470e320a1cd0522ac49c63956ea6d12d` / `7d99e722c6e27b7257a709182a0827b63c4a1599cfe14f3472e9e4a914cf8ad1` |
| Compact verifier source | SHA-256 `a7b6ebd0fbd69001e34b874fff0dba1c6d9ecc1e6dae682318a410074b537b90` |

The saved verifier's input list contains the group02 notebook output and private parent payload. Kaggle's draft source-update console reported `sourceId:362625674` for the training notebook; the saved proof source was then bound by the separately observed version link. The notebook source list did not display an explicit immutable `isSourceIdPinned:true` flag, so version binding is documented by the observed source ID, links and content hashes rather than that flag alone. The original group02 saved output and the existing group03 readback both report archive bytes, SHA and CRC. These checks are repeated inside the compact verifier.

| Shard | Original archive bytes | Original archive SHA-256 | Compact proof bytes | Compact proof SHA-256 | Ordered jobset SHA-256 |
| --- | ---: | --- | ---: | --- | --- |
| `shard_0002` | 61,939,216 | `409c523b421397fecc22bc953a13b2642aa49cf1f0f443c9e88f1d11af4ca908` | 21,388 | `735a225b2c6253b3357c325ae09735110fe39956c17e0dbbec037e064218a99b` | `1cf89024e9c8b9d8488b386a54a0995924fad19a9334f9539d50843d345260f1` |
| `shard_0003` | 62,632,926 | `f7f5073878345a4cb44f1e293a7bfd1e1c762244475cf10e7bba40167c66430b` | 21,346 | `e23351b9593f1703a075e9fb2ddc935d35f52c43469dbd1b3c59db32fab7e5d8` | `145d75ce5a847f1494d7ec4285e47812c769acb7206bc0da7a20a48e4545f4d8` |

## Remote execution and readback

1. [`hung-compact-proof-group02-20261028-v1`, saved version `363105577`](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-group02-20261028-v1?scriptVersionId=363105577) ran successfully on CPU in 70.5 seconds. The terminal output lists both compact proof files and logs `40` verified rows with the byte counts and SHA-256 values above. The draft preflight produced exactly the same values.
2. [`hung-compact-proof-group02-readback-20261028-v1`, saved version `363107432`](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-group02-readback-20261028-v1?scriptVersionId=363107432) ran successfully on CPU in 11.4 seconds. Its saved input lists the proof notebook. It independently reopened both proof files, recomputed exact bytes and SHA, checked archive fingerprints, two disjoint 20-job sets, row statuses, and both ordered jobset hashes. The output tab lists `hung-compact-proof-group02-readback-20261028-v1.json` (2.21 kB) with `jobs:40` and `status:REMOTE_PROOF_READBACK_VERIFIED`.

The compact proof checks each job's receipt/manifest hash, its referenced archive members and log bytes, the ZIP member CRCs, provider pins, and the exact expected jobset. The readback verifies the saved proof artifacts independently. The 40 per-job rows remain in those remote compact proof JSON files. They are not yet imported into a local 782-row ledger. Together with the previous shard0001 proof, **60/560 Kaggle jobs have remote compact proof and independent readback**; this is not a claim that Development is complete or reviewer accepted.

## Source and lint fidelity

The Git notebook files are the submitted saved sources. Ruff's default notebook format and import checks would rewrite them after execution, which would break correspondence to the saved Kaggle versions. `pyproject.toml` therefore excludes only the six exact immutable compact-proof notebook paths, including the earlier shard0001 attempts and these group02 notebooks. Future source notebooks should be linted before their first saved execution, or added as exact immutable snapshots only with a recorded reason. This exclusion does not cover project Python modules or other notebooks.
