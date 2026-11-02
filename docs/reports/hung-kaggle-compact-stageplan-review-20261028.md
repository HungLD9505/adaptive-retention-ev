# Kaggle compact proof stage-plan review (2026-10-28)

## Reviewer finding and correction

PR #72 received a P1 changes-requested review: the first compact verifier trusted the stage keys in each archived job receipt. A matching archive SHA alone did not prove that the receipt listed every stage required by the frozen job/config plan. Its 180 row-level proofs remain immutable historical evidence, but they are not promoted to exact-stage Development acceptance.

`tools/hung_kaggle_compact_proof.py` now emits proof schema `hung-kaggle-compact-shard-proof-v2`. It derives each job's required stages from its pinned method, target checkpoint state, replay block length, and replay limit. The split follows `verification_split_limit`: `min(3 * block_days, max_origins - 1)`. Target-only requires `target-only-init`; a controller with a missing target checkpoint requires `target`. Every method requires both split and terminal replay stages.

The v2 verifier requires an exact receipt stage set, exact archived member inventory, and stage receipt bindings to plan, partition, cell, config, job, module, and selected command arguments. It checks a nonempty execution log and its command header; manifest status, run ID, code commit and executed-source identity; the stage-specific checkpoint SHA; the controller event journal or single-baseline forecast journal SHA; and the required measurement and manifest files. It also checks dispatch identity schema, code commit, full plan job/stage counts, archive bytes/SHA, every referenced file SHA, and ZIP CRC. Kaggle version IDs in a proof remain caller claims until independently authenticated from saved source/readback pages.

## Regression and pilot scope

`tests/test_hung_kaggle_compact_proof.py` has a valid three-stage target-only fixture and rejection cases for empty, subset, unexpected stages, missing runner checkpoint, missing forecast journal, an unreceipted archive member, a failed manifest, and archive SHA mismatch. These are synthetic code regressions, not remote proof of the original 180 jobs.

The first create-once CPU pilot `experiments/hung_sprint2/kaggle_compact_proof_shard0001_stageplan_v2.ipynb` embedded verifier SHA-256 `75b80532ad5d7149f461a6260c4a3c630a03007059a98c2790e9d878b085cf10`. Saved Kaggle version `363118896` of `hungluongduc/hung-compact-proof-shard0001-stageplan-20261028-v2` **failed** before archive verification with `KeyError: 'value'`. This exposed a mismatch in the pilot: frozen plan config entries contain `id`, `path`, and `sha256`; the official dispatcher loads `value` separately from the config file. The failed saved version and its log remain intact and contribute zero accepted rows.

The corrected verifier requires raw config bytes, hashes each against both frozen parent and relocated provider plan SHA pins, and uses the parsed values for complete-plan stage count and per-job stage derivation. Regression cases now reject missing and changed config bytes. The new create-once notebook `experiments/hung_sprint2/kaggle_compact_proof_shard0001_stageplan_v3.ipynb` reads config bytes from the pinned payload ZIP without extraction. Its embedded verifier SHA-256 is `412c5d3c2802f6c9ba072cef2efc80e9b6ea71bc0776f3468d6a638e573e77e5`; it writes only to `hung-compact-proof-shard0001-20261028-v3`. Remote execution and independent readback are pending at this checkpoint.

The remaining shards must use fresh v2 saved versions and independent readback before v2 rows can replace the limited v1 status. No previous proof, archive, receipt, or report was overwritten.
