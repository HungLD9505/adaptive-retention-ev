# Local exact-stage readback of Kaggle group06 (2026-10-28)

The official Kaggle CLI downloaded three immutable `artifacts.zip` files from [group06 training saved version 362841662](https://www.kaggle.com/code/hungluongduc/hung-matched-group06-44b8532-20261027-v2?scriptVersionId=362841662), ordinal `/1`, into a new ignored drive-D directory. Their total is 187,951,741 bytes. Three saved shard receipts were downloaded separately. The independent [CPU readback saved version 362883097](https://www.kaggle.com/code/hungluongduc/hung-output-g06-readback-20261027-v1?scriptVersionId=362883097) has a `passed:true` saved receipt, SHA-256 `b2dcd6a01fb0e2fe00fec392c7fc6d610e3909aa60ac24229787c55c5a5662f0`, listing the same three archive bytes/SHA and CRC `passed`.

The group06 provider plan/partition were generated create-only by the established group-prefix/SHA transformation of saved group03 plan bytes. The resulting plan SHA-256 `2e9faad307c29ca681eedcc0f64da2ab6ec00ef3893a280d1aead08b30d16836` and partition SHA-256 `7750cfc08778c747122a2a2e82190a63c5e2f034d68f690748290c599b7c41be` match every saved group06 shard receipt. The parent plan/partition and frozen config bundle came from saved payload bytes.

| Shard | Saved archive bytes | Saved archive SHA-256 | New local proof SHA-256 | Jobs |
| --- | ---: | --- | --- | ---: |
| `shard_0026` | 70,222,453 | `326d0948c17201e9dee95afe9aa5d99376a5626bc0253e77aaa1e6e26dc3e971` | `9c006c610e979a4d285f550aeff3a4913bd006d658325021d5658e4ca2edd359` | 20 |
| `shard_0027` | 70,822,245 | `baec1bf8527d1fdb9e386621fdc10e9feee07e5ea826064050b0251d5ee577c4` | `ef58d6165c948391538d3ac19d1aa6fec68ec8af9f142a86dd2c13a25c44266d` | 20 |
| `shard_0028` | 46,907,043 | `5a5ef4fd05b82be4db824af93ec3c815af10a5ad42d08991100394635ef770db` | `7b727ee21049ac6f48df30a165b8a67b06e8ac177537c28070abced163b932e7` | 20 |

The corrected verifier `tools/hung_kaggle_compact_proof.py` checked exact archive bytes/SHA, ZIP CRC, jobsets, receipt/manifest references, mandatory stage plans, config bytes and checkpoint/log references. Each run exited zero. The three create-only proof JSONs under `.cache/kaggle-proof-group06-stageplan-20261028/` contain 20 distinct `VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN` rows each. Across shard0001 and groups02–06, **480/560 Kaggle jobs** have corrected local exact-stage proof outside a new ledger snapshot. The published v4 ledger remains 222/782 locally byte-verified; 80 Kaggle jobs still need this check. Independent peer acceptance remains open. No training job was submitted or rerun.
