# Actual Kaggle/local reconciliation — 27 October 2026

Related: #22, #23, #10, #39; PR #72. `docs/SPRINT_PLAN.md` remains the schedule.

## Execution and durability snapshot

262 of 782 new Development jobs have completed-shard evidence and remote SHA/CRC
readback; 520 remain outside completed-shard certification. The 262 comprise 142
local jobs and 120 Kaggle jobs. Historical Main69 is separate and counted once.
Block7 remains unmatched. No independent acceptance or Final execution is claimed.

Kaggle recovery v2 completed shard0010 and persisted its 66,147,049-byte archive,
SHA `c83b3af82e5eedc2c4b68d0bb1d808b10e66fb037708bb5345c38ae3c602b180`.
Its private Dataset v1 has separate CPU readback evidence. Upload took 9.252s;
upload plus readback took 48.759s. This is a measured durability cost, not the
whole-job GPU runtime. The running queues handle subsequent assigned shards.

Local shards0031 and0032 now have a private persistent 237,036,596-byte capsule,
SHA `78449c917ebea4d719042c5849b095bf73f44a1f519cce1bbe86e0397df69675`.
[Dataset v1](https://www.kaggle.com/datasets/hungluongduc/hung-local3132-review-capsule-20261027-v1/versions/1)
contains the archive, pinned helper and transport manifest. A separate
[CPU readback 362667223](https://www.kaggle.com/code/hungluongduc/hung-local3132-cpu-readback-20261027-v1?scriptVersionId=362667223)
passed in 36.3s, with 19.143s verification/scoring: Main69 plus 40 new local jobs,
59 scorable runs, CRC passed. Main anchors repeat physically across capsules but
are counted once logically. See `hung-local3132-remote-readback-20261027.json`.

## Actual metric reconciliation

[CPU exporter 362667983](https://www.kaggle.com/code/hungluongduc/hung-portable-shard0008-cpu-export-20261027-v2?scriptVersionId=362667983)
passed in 21.7s without GPU or Internet. It rechecked the exact original CPU receiver
proof and relocated mounted paths while retaining all content hashes. It did not
train or repeat official replay verification. The 270,418-byte daily-error export
was read back to local through 30 compressed log chunks and matched SHA
`b7b28cb8c70c75a5268ae94b9026a0ec67d53a5d36f0aa6a51b4e24fefc0035e`.
The earlier v1 draft never submitted a version: its Script editor remained loading.
The working v2 used the same frozen source through a Dataset-created editor.

The local through-shard0032 collection was independently exported and combined
with Kaggle shard0008 using exact expected disjoint job sets from the canonical
partition. [Hybrid report](hung-development-hybrid-20261027-v1/report.md):

| Collection | Runs | Scorable | Zero scored |
|---|---:|---:|---:|
| Main69 + local142 + Kaggle20 | 231 | 123 | 108 |

There are 91 paired cells and 75 blocked pairs. Another 100 completed new jobs
are outside this particular metric collection; missing metric inclusion is not
evidence that those jobs were never executed. Zero scored days do not mean zero
error. Local-only snapshot v5 has 211 runs, 112 scorable and 99 zero-scored.

Per-day absolute and squared hourly errors are in original kWh units. MAE is
`sum(abs(error)) / (24 * scored_days)`; RMSE is the square root of the corresponding
mean squared hourly error. Pairing uses identical input/initialization and the
intersection of scored days with equal label hashes. Seed means are formed within
station, then stations receive equal weight within each budget. Transfer gain and
negative transfer apply only to Source-using methods versus Target-only. Rows can
have different cohorts; the table does not rank all methods globally.

The companion JSON pins the transport, merge specification, combined result,
exporter/scorer, receiver, plan and artifact evidence. Raw checkpoints, archives
and full daily-error exports remain outside Git. No historical run was renamed.
`hung-hybrid-input-config-pins-20261027.json` additionally records the model and
historical code commits, input ZIP SHA, 80 canonical config-file pins, 69 input-cell
pins and all 231 included run/Source/Target/manifest/checkpoint bindings. Listing
the canonical matrix does not assert every configuration has finished or passed
independent review.

## Checks and remaining gates

`python -m unittest discover -s tests`: 357 tests, one skip, exit 0 on clean code
head `a26180c3f33898b24c21fe7ca2a931e855fec1f6`. Ruff check/format and
`git diff --check` passed. CI passed on both Ubuntu and Windows at
`29752229fda9e82e0e2429b8639d49cae16c495a`; subsequent notebook/report additions
have separate CI status. Actual export CLI and Python reconciliation API runs
are recorded in the local evidence logs and report hashes.

Full Development coverage and the remaining paired metrics, independent review,
Block7 fairness disposition, all required baseline/ablation/budget/seed coverage,
and immutable Final lock remain incomplete. Final labels were not used. #39's
Kaggle/local alternative still needs explicit team acceptance. This supplies #10
with real partial Results/Discussion/Limitations evidence, not a completed Final.
