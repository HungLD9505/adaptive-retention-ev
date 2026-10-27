# CPU session capacity recovery — 2026-10-27

**402/782 new Development jobs now completed and independently remotely read back;380 remain.** Main69 and unmatched Block7 remain separate. No full-objective or Final acceptance is claimed.

## Actual failure and preserved evidence

[GPU recovery13 version362690241](https://www.kaggle.com/code/hungluongduc/hung-group03-shard13-recovery-20261027-v1?scriptVersionId=362690241) completed successfully in2380.1s total. Its20-job execution receipt reports1824.033602933s; these two costs must not be conflated. Archive453,014,419 bytes SHA **49442d6a54209957e2fc008f3f7891b5160c7a9e23fa7c5eee7c49f46f710b51**, execution/local verification exit0 and CRC passed. [Original receipt](evidence/hung-shard0013-output-receipt-20261027.json) remains unchanged, including its originally pending remote-readback field; subsequent proof is separate.

The recovery CPU controller362690145 then failed while creating the intended CPU readback: **Maximum batch CPU session count of5 reached**, response version0/emptyURL. Four controller/worker slots plus the newly scheduled CPU work exhausted capacity. The readback was not executed, but native inspection found a persisted owned **draft0**. Version0 rejection therefore does not prove that no kernel resource exists. Its claim/source SHA52b0acfd248deedbcfe1f4635eb4fd33f665410fe2bc630a06283d502797f9f1 and allocation SHA were inspected; both claim and draft remain untouched. A proposed adoption was abandoned after that preflight contradicted absence; no original identity was retried and no training was repeated.

## Controlled repair and proof

The idle export coordinator362673642 was intentionally canceled at9187.5s, before its3-hour handoff. It had only submitted/completed batch00; its receipt was captured and the independent batch00 Output/export remains preserved. The waiting output controller362696128 was canceled at2787.1s, before any successor GPU acknowledgement. Native reloaded Logs confirmed both cancellations. No completed model job was canceled.

A fresh CPU identity [readback v2, version362709067](https://www.kaggle.com/code/hungluongduc/hung-g03-s13-readback-20261027-v2?scriptVersionId=362709067) mounted the exact completed GPU Output version362690241 and ran the unchanged original readback program SHA52b0acfd248deedbcfe1f4635eb4fd33f665410fe2bc630a06283d502797f9f1. **It succeeded69.1s** and independently verified bytes/SHA/CRC/runtime plan/partition/exact jobsets for8–13. Prior8–12 archives were carried/read, not trained or counted again. Only the new20 jobs increase the completed/remote-verified snapshot from382 to402.

## Resumed pipeline

[CPU relay01 version362710032](https://www.kaggle.com/code/hungluongduc/hung-output-relay-01-20261027-v1?scriptVersionId=362710032) resumes group index2,ordinal1,predecessor phase, using the new readback-v2 identity. It preserves the canonical plan/allocation and **every GPU/CPU child-program SHA for all380 successor jobs** from the original immutable output manifest. A separate resume manifest records only this proof-handle/ordinal repair; no old plan/receipt/run identity is rewritten.

The relay actually read current free GPU quota **64,457.045876s**, required17,178s, then submitted [group04 version362710139](https://www.kaggle.com/code/hungluongduc/hung-matched-group04-44b8532-20261027-v2?scriptVersionId=362710139) once, with no invalid sources. Actual source SHA **fdedc6f709536e8de40ad1e7b003f2deb255b0ec8c68794bb2d66730a83b4b62** matches the original manifest. Group04 covers14–19; later groups remain gated by actual predecessor completion/readback, fresh quota, parity and disk reserves. New resume program SHA **381225ad2c452ef42587fcd416b920e0cc4457b5c84b3dec529b55273c7b0e03**. No full-matrix single-session execution or Final is enabled.

CPU working budget is now two long-lived controllers (metrics + output), one metric receiver, one independent output readback, with one slot left for handoff against the observed5-session limit. **Do not restart the idle export coordinator during this training/verification phase.** The existing metric queue continues to use the original reader identities; no completed receiver is resubmitted.

Prepared, **not launched**: `kaggle_export_deferred_resume01_v1.ipynb`, source SHA **000812306fb6bd5dc41d1ff125b5d2c9ef9522a5c07b33ed5c81465d1d8c68b7**. It requires every remaining metric reader to be observed COMPLETE at exact version1 before starting batches1–6 (480 jobs),ordinal1,submittedFalse. Batch00's80-job export and SHA remain reused. This one later reporting milestone avoids a third idle controller occupying a CPU slot throughout training.

## Validation and reporting limits

The unchanged Python execution/verification core passed393 tests/1skip/exit0 at30fe7d1. New recovery packets compiled and every generated GPU/CPU child SHA was compared against the original manifest. Offline simulation of the new proof mapping confirmed group14 dispatch followed by an acknowledged-GPU handoff to relay02 in phasegpu, with no duplicate execution; no actual provider calls were made by that simulation. Repository-wide Ruff/diff checks pass. The real CPU readback and successful GPU submission provide separate integration evidence.

Prepared unused adoption scratch code was removed from our uncommitted changes; historical files and failed logs remain preserved. Response0 is explicitly not treated as proof of resource absence. Dataset status/download permission errors were not retried, no protected endpoint fallback or usage reset was used.

[Hybrid v4](hung-development-hybrid-20261027-v4/report.md) remains371 unique runs/196 scorable/175 zero-scored/166 paired cells/142 blocked pairs, with [exact code/config/input/run provenance](hung-hybrid-v4-provenance-20261027.json). It is a historical metric snapshot;100 now-completed GPU jobs remain outside that collection pending metric restoration/export. No effectiveness or Final claim. Independent review/Block7 disposition/#39 provider substitute acceptance and immutable Final lock remain pending; no merge, issue closure or main promotion.

Files added for recovery: `kaggle_shard0013_output_readback_v2.ipynb`, `kaggle_output_dispatch_resume01_v1.ipynb`, its resume manifest, `kaggle_export_deferred_resume01_v1.ipynb`, this report/JSON and the original shard13 receipt copy. Existing Python/model methods and the original immutable manifest are unchanged. Commands: exact frozen-source AST extraction, five-group GPU/CPU SHA equality checks, simulated resume/handoff validation, source compilation, Ruff lint/format and git diff--check. Native actions: cancel only the two idle controllers, save a new CPU readback once, then save relay01 once after proof. All source/failed/canceled evidence links and raw logs remain available.
