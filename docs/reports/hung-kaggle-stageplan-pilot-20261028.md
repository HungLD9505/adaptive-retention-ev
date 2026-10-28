# Kaggle exact-stage proof pilot — 28 October 2026

The [create-once CPU saved version `363123440`](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-shard0001-stageplan-20261028-v3?scriptVersionId=363123440) of `hungluongduc/hung-compact-proof-shard0001-stageplan-20261028-v3` completed successfully in 39.0 seconds. The saved notebook displayed two pinned dataset inputs, CPU accelerator `None`, and the terminal JSON line:

```json
{"jobs": 20, "proof_bytes": 21699, "proof_sha256": "14ab3b12684f6358f628d1cc083470655acadde84ab8c0b475582abc64de2e11", "shard": "shard_0001", "status": "VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN", "version_ids_independently_authenticated": false}
```

The notebook source was imported from [the committed v3 notebook](../../experiments/hung_sprint2/kaggle_compact_proof_shard0001_stageplan_v3.ipynb). It pins the corrected verifier SHA-256 `412c5d3c2802f6c9ba072cef2efc80e9b6ea71bc0776f3468d6a638e573e77e5`, frozen payload and shard dataset identities, original archive bytes/SHA and 20-job shard set. This observed saved result establishes that the corrected verifier can execute on one original archive; it does not independently authenticate the caller-supplied original training/readback version IDs.

The separate [CPU readback source](../../experiments/hung_sprint2/kaggle_compact_proof_shard0001_stageplan_readback_v1.py) is prepared and linted but **has not been saved or run**. It must attach only the saved output of version `363123440`, verify the exact proof bytes/SHA, schema, stage receipt/manifest maps and ordered jobset hash, then publish a create-only receipt. Until that independent readback and ledger import pass, all 180 v1 rows remain provisional and no Kaggle job is promoted to accepted per-job proof. The 380 other Kaggle jobs still lack proof bytes in Git. No training or Final workload was rerun.
