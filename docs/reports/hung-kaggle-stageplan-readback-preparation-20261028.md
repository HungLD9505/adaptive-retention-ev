# Exact-stage Kaggle proof: independent readback preparation (2026-10-28)

The saved CPU pilot [version 363123440](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-shard0001-stageplan-20261028-v3?scriptVersionId=363123440) finished successfully for `shard_0001` (20 jobs). Its displayed summary reports `VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN`, `proof_bytes=21699`, and proof SHA-256 `14ab3b12684f6358f628d1cc083470655acadde84ab8c0b475582abc64de2e11`.

An independent CPU readback is prepared in `experiments/hung_sprint2/kaggle_compact_proof_shard0001_stageplan_readback_v1.ipynb` and the corresponding Python source. It pins the expected saved proof bytes, SHA-256, schema, 20 distinct job IDs, and ordered jobset SHA-256. The script writes a new readback JSON using exclusive creation.

The new Kaggle draft `notebookb873374c4a` remained at **Loading Editor** on this check, even after a page reload. Its File menu showed Import Notebook disabled. The readback notebook has **not** been imported or run, and no proof row has been promoted on this basis.

When the editor becomes available, import the prepared notebook into a new notebook, attach only the saved output from version `363123440`, select CPU (`Accelerator: None`), and save one named run. First inspect whether a version already exists to avoid duplicate execution. Validate the saved output file and source version metadata before ledger promotion. The v3 pilot does not imply acceptance of the other 540 Kaggle jobs.
