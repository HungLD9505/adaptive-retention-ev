# Local exact-stage readback of Kaggle group03 (2026-10-28)

The official Kaggle CLI downloaded the immutable [group03 recovery training output, saved version 362690241](https://www.kaggle.com/code/hungluongduc/hung-group03-shard13-recovery-20261027-v1?scriptVersionId=362690241), ordinal `/1`, into a new ignored directory on drive D. The selected six `artifacts.zip` files and receipts total 1,432,554,597 bytes. The exact parent/provider plan files came from the earlier saved [group03 compact-proof output, version 363111778](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-group03-20261028-v1?scriptVersionId=363111778). The frozen configuration bundle was `.cache/kaggle-payload-v2/provider-payload.zip.bin`. The corrected local exact-stage verifier `tools/hung_kaggle_compact_proof.py` has SHA-256 `412c5d3c2802f6c9ba072cef2efc80e9b6ea71bc0776f3468d6a638e573e77e5`.

| Shard | Saved archive bytes | Saved archive SHA-256 | New local proof SHA-256 | Jobs |
| --- | ---: | --- | --- | ---: |
| `shard_0008` | 74,362,442 | `a49fc9c6c56b5e6cdcf54bb1af15d05cb511d017f3be3cb4abfb41f17dc151e8` | `861a2dc5917280aa1dddee90f15d15b0ba00300ff19fb841784dfb705bc7f907` | 20 |
| `shard_0009` | 68,786,447 | `37f635185da5bf08fd927e0ecacb9efb53f41f2b87f85ad3554f5a92ee53de5e` | `8e8603cfe0d78393fba123f41d8cf99647719d508b4f2dab30e0bd73dddb9760` | 20 |
| `shard_0010` | 66,147,049 | `c83b3af82e5eedc2c4b68d0bb1d808b10e66fb037708bb5345c38ae3c602b180` | `b65be0dcd8f57e9bbfc61ecae639fe6ad7e98d7648893bf4f7faf28038112b7a` | 20 |
| `shard_0011` | 317,485,131 | `959dbb76e407ac6c1ff7fce723fdc1510046280b1b473902ede231ff79bcfc6b` | `3df0ba6f701e0fcd3f73b3d922ee6999abf19f00e71de6574a2408c1cf400663` | 20 |
| `shard_0012` | 452,751,164 | `d0f7f0335745843adbf16b5c05aafd7fb7a4505ba13c92ab649849677d9b92dc` | `98ab56e65f0fff452e1dc30e92787baa2ac8e87b54b9292cbe0cb1afafe89658` | 20 |
| `shard_0013` | 453,014,419 | `49442d6a54209957e2fc008f3f7891b5160c7a9e23fa7c5eee7c49f46f710b51` | `d73c743bf3391b73ecac2c644b477b64f359f3be86dd258850214f9b7d9fc94f` | 20 |

All six create-only JSON files under `.cache/kaggle-proof-group03-stageplan-20261028/` contain 20 distinct rows with status `VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN`; their union has 120 unique job IDs. The verifier reopened the original archive members and checked the frozen jobsets, receipt/manifest references, mandatory stage set, config bytes, checkpoint/log references and ZIP CRC. It exited zero for every shard. Archive fingerprints match the earlier independent [CPU readback](hung-kaggle-compact-proof-group03-20261028.md), version 362709067. No training or new Kaggle proof job was submitted.

Together with shard0001 and group02, **180/560 Kaggle jobs now have corrected local exact-stage proof outside a new ledger snapshot**. The published 782-row v4 ledger still records only 222 locally byte-verified jobs; its provisional v1 Kaggle rows must not be promoted by this report alone. The remaining 380 Kaggle jobs require saved archive downloads and the same verifier. Independent peer acceptance remains pending.
