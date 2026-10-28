# Kaggle compact per-job proof: shard0001

**Scope:** Development-only, 20 already trained jobs in `shard_0001`. This is a CPU verification route over immutable saved outputs. It does not rerun training or establish reviewer acceptance.

## Pinned sources

| Item | Saved identity / fingerprint |
| --- | --- |
| Training notebook | `hung-matched-shard0001-44b8532-20261027`, saved version `362612528` |
| Independent archive readback | `hung-dev-readback-shard0001-20261027-v2`, saved version `362633606` |
| Private archive dataset | `hung-dev-shard0001-44b8532-20261027-v2`, dataset version 1 |
| Archive | `65,931,034` bytes; SHA-256 `29e3db51106402942959f80762e4c27995ad4ec9f2253fd96cc8a4681d3b2dcd` |
| Private model payload | `hung-matched-payload-44b8532-20261027-v1`, dataset version 1; `149,838,818` bytes; SHA-256 `23a6d420523d990d07ff07d814ed642a851925283a102a3ae806f3b666e1d6f4` |
| Derived provider plan | SHA-256 `80a1666cf2083594c9a2bc0b0a4dc3e30118eda43d07187cd5b6d8b51f90e0bb` |
| Derived partition | SHA-256 `e2c6cb6f15a7473c6cdfd7912fefa838d63a770cf352dff93c2cccc3ae86a15c` |
| Compact verifier source | SHA-256 `a7b6ebd0fbd69001e34b874fff0dba1c6d9ecc1e6dae682318a410074b537b90` |

The derived provider plan and partition were reconstructed locally from the pinned transport with the original Kaggle execution path. Their hashes matched the original saved training receipt. The Kaggle draft console independently observed the mounted payload file at 149,838,818 bytes and its pinned SHA-256. The saved source lists both private dataset inputs.

## Execution attempts

| Saved proof version | Result | Evidence |
| --- | --- | --- |
| [v1 `363097232`](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-shard0001-20261028-v1?scriptVersionId=363097232) | Failed before archive read | The first notebook used the short `/kaggle/input/<slug>/` path. Kaggle mounted the dataset at `/kaggle/input/datasets/hungluongduc/<slug>/`. No proof rows were produced. |
| [v2 `363098042`](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-shard0001-20261028-v1?scriptVersionId=363098042) | Failed before payload read | The corrected archive path existed. A non-interactive `kagglehub.dataset_download` tried to attach the private payload and Kaggle rejected it: `New Datasets cannot be attached in non-interactive sessions`. No proof rows were produced. |
| [v3 `363099687`](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-shard0001-20261028-v1?scriptVersionId=363099687) | Successfully ran in 16.0 seconds | Both datasets were attached through the notebook editor before saving. Saved output contains `compact-proof.json` (21,399 bytes), parent/provider plan files; log reports 20 verified rows and SHA-256 `75862528c5d56a27fd5c164c616faf69bcff5c7b23451e09c20ffcdae2cd87e6`. |

The interactive v3 draft preflight ran the same verifier on the two mounted inputs and reported `20` rows with `VERIFIED_ARCHIVE_BYTES`, proof size `21,399` bytes and the same SHA as the terminal saved v3 log. The draft CPU session was stopped after the saved v3 was submitted. [Independent CPU readback](https://www.kaggle.com/code/hungluongduc/hung-compact-proof-shard0001-readback-20261028-v1?scriptVersionId=363102461) saved version `363102461` successfully ran in 9.2 seconds. Its saved input tab visibly lists v3's `compact-proof.json`. It recomputed the exact `21,399` bytes and SHA-256 `75862528c5d56a27fd5c164c616faf69bcff5c7b23451e09c20ffcdae2cd87e6`, confirmed 20 unique rows and the frozen ordered jobset SHA-256 `e2051de08dfb0f0ee91c3617151f08d5cd2c712bb88344244980e4ec2f350c69`, and wrote a new `REMOTE_PROOF_READBACK_VERIFIED` receipt. The readback output page reported 1.02 kB. This is a remote proof for one 20-job shard; it is not a consolidated 782-row Development ledger.

## Acceptance boundary

The notebook verifies the exact shard jobset, parent/provider scientific pins, compressed archive bytes and SHA, every ZIP member CRC, job/stage receipt SHA, referenced member/log SHA, and completed run manifest identity. Its two version IDs are caller claims, although the original training/readback version links were separately observed and the saved source pages list the mounted inputs. The per-job receipt/manifest hashes remain inside remote `compact-proof.json`; they have not been ingested into a local versioned 782-row ledger. Keep the local v2 ledger at 222 locally verified rows and treat these 20 Kaggle rows as separately verified remote proof pending ledger import and peer review. No `560/560` claim follows from this first-shard result.
