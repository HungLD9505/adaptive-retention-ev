# Local completion and output-gated Development dispatch — 2026-10-27

**Full objective incomplete.**382/782 new jobs have completed and independent remote SHA/CRC readback.400 remain uncertified, including the running shard13 and380 fixed successor jobs. Historical Main69 and unmatched Block7 remain separate.

## Verified local completion

All222 assigned local jobs completed: pilot6 + remainder39's16 + fixed worker queue200 (10×20). `local-development-worker-v1/complete.json` records200 queued jobs, not222 by itself. Both the GPU worker and CPU report process ended after terminal completion records; no failure/ongoing-process claim is inferred from stale lockfiles. CPU report through7 contains291 runs (Main69+local222),154 scorable/137 zero-scored; its final completion marker confirms all local snapshots.

The last80 jobs (shards4–7) were individually checked against execute/verify exit0 and exact log hashes, archive bytes/SHA/CRC, then packaged with unchanged69 Main anchors. The private [Dataset version1](https://www.kaggle.com/datasets/hungluongduc/hung-local0407-review-capsule-20261027-v1/versions/1) contains369,295,643-byte capsule SHA **237aee82487d32ea9da8f42b4aaf91a9695765491f3da91875744cf3b5155957**, helper and transport receipt. It stays private; reviewer access/acceptance is separate.

[Independent CPU readback362699093](https://www.kaggle.com/code/hungluongduc/hung-local0407-cpu-readback-20261027-v1?scriptVersionId=362699093) **succeeded45.7s**. Actual SHA/CRC/checkpoint/forecast scoring took33.626378262s, recomputed149 runs (Main69+new80),78 scorable. Python3.13.15/Torch2.11.0+cpu; helper SHA78c4bd421ec0971023dca141ed8e81b22dbc97fe5c5855cd2511bfb30d1761be. No training/Final. Main anchors are counted once across all capsules. Exact upload-only elapsed time was not captured and is left null.

The DataFrame-download Code dialog still showed awaiting compression. The supported native static-input workflow nevertheless exposed all three files and allowed explicit pinning to version1; the separate CPU process then actually read and verified them. Neither the upload acknowledgement nor file tree alone is treated as successful durability. No denied Dataset status/download endpoint was retried, no API bypass or duplicate version was used.

## Automated remaining groups

The [output controller362696128](https://www.kaggle.com/code/hungluongduc/hung-output-relay-00-20261027-v1?scriptVersionId=362696128) is actually RUNNING, CPU-only, waiting for recovery13's completed GPU version and independent CPU readback. It will execute only existing groups14–19,20–25,26–28,33–34,35–36, preserving original names/base/runtime plan and jobset fingerprints. The393-test source30fe7d1 was frozen and tested before this native Save & Run All. No successor GPU had been submitted at the recorded observation.

Each group requires current quota+reserve, original parity/disk/execution guards and a separately completed CPU SHA/CRC readback of private Output version1 before the next group. Three-hour CPU handoff carries exact phase and acknowledged child identity, avoiding duplicate GPU/readback submissions; twelve relays bound the chain. Manifest SHA **167eedc010cd9a216fa14eac96c35b80f1664f965b6e4de424e64f53492c7ac8**, launcher SHA **f4a41b7689f6899979c9c1f76edae5bbea7c4080d7fb72d61f51f3ef6cb8f690**. See [implementation and constraints](hung-output-dispatcher-20261027.md). It is not a Final dispatcher and does not select configurations from scores. Capacity guards are estimates checked against current quota, not a promise that the whole remaining matrix fits one reservation.

Existing CPU metrics362690764 and export362673642 remain separate programs. Their original reader names and seven80-job batch allocation are preserved; no duplicate coordinator or completed batch was launched. Codex need not monitor individual jobs.

## Actual partial Results handoff

[Hybrid v4](hung-development-hybrid-20261027-v4/report.md) has371 unique runs=Main69+local222+Kaggle80;196 scorable/175 zero-scored,166 paired cells/142 blocked pairs. Another80 completed GPU jobs are outside the metric collection pending CPU restoration/export. No global ranking or effectiveness/Final claim.

Only the predefined newly completed shard7's20 runs were exported from the authenticated through7 catalog; their exact immutable jobset hash was checked. Existing local271 and GPU80 portable exports were reused, preserving original provenance and avoiding rescoring/retraining prior runs. The merge enforces disjoint expected jobsets, exact daily label-hash intersection and station-first paired MAE/RMSE, gain and negative-transfer rules. Full result SHAbfdff9be47653c25ea5e15049b35e9148f4dfffc750a4249ec5afd0ccf73f39c; spec SHA f1eb33723e9cb9b6038b02cc38a14a7e16b7652e2dd8e232505720d2d6d09446. Large artifacts/daily errors remain outside Git.

## Validation, review and pending work

- `python -m unittest discover -s tests`:**393 tests,1skip,exit0**,159.877s suite,167.0402391s wrapper, clean source30fe7d196d9e3ede954384089790e718aa314d32. `.cache/provider-offline-tests-v22.log` and exit receipt retain proof.
- Focused output-queue/status suite28 tests passed. Initial package check exposed Windows default-decoding corruption; explicit UTF-8 fixed the reader without changing expected hashes. New tests cover all five barriers, malformed/missing proofs, quota, exactv1 request, interrupted atomic receipts and acknowledged-child handoff.
- Repository-wide Ruff lint/format and diff checks pass; native readback is actual runtime validation of the new thin capsule notebook. Capsule builder and local score verification both exited0. A one-off preliminary local receipt check expected GPU-style exit fields and stopped; corrected inspection used the separate authentic execute/verify exit receipts. No historical receipt was rewritten.
- Latest inspected heads:#66 c269cfa181981224198f3d8535f8c87135e62620;#68 315113f73840e0f36d1930ae0373d6b61fe0e6f9. PR70/72 still have zero review submissions. #39 still has five comments and no independent acceptance of the Kaggle/local substitute. These are GitHub review facts, not live-process evidence.

Next: let existing recovery/controller/metric/export programs advance. Ingest only exact completed80-job batches. Diagnose a concrete terminal failure before creating any new claim or recovery; preserve partial outputs. Independent code/fairness review, #39 substitute decision, complete Development coverage, all baseline/ablation/budget/seed evidence and immutable independent Final lock still precede Final. No merges, issue closure, main promotion, usage resets or Final labels were used. `docs/SPRINT_PLAN.md` remains the sole schedule.

Files in this phase: tools/hung_kaggle_output_queue.py; tools/hung_kaggle_queue.py; tests/test_hung_kaggle_output_queue.py; tests/test_hung_kaggle_queue.py; experiments/hung_sprint2/kaggle_output_dispatch_cpu_v1.ipynb; kaggle_output_dispatch_manifest_v1.json; kaggle_local0407_readback_v1.ipynb; docs/reports/hung-output-dispatcher-20261027.md; this report/JSON; hybrid-v4 report.md,summary.json,paired.csv.

Commands: focused/full unittest, Ruff check/format, git diff--check, exact source/manifest AST hashing, capsule build/verify--score, bounded shard7 portable export and existing merge/publish functions, native Kaggle private upload/Save & Run, git commit/push. Raw SHA-pinned outputs are retained in project.cache.
