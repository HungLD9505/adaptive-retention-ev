# Autonomous group-03 start and metric definitions v2 — 2026-10-27

Kaggle group 02 actually completed its 40 jobs in **3,761.7 provider seconds**.
The ordinary Python CPU coordinator then submitted GPU group 03 without another
manual Save Version. [Group 03, version 1](https://www.kaggle.com/code/hungluongduc/hung-matched-group03-44b8532-20261027-v2)
is running on T4 x2 with submitted source SHA
`41cf557ec06f966b5165a790e9cb0eb9eda1c6d58c3df12722716678a4433d0d`.
Its runtime independently read both predecessor archives with exact SHA/CRC,
canonical job sets and expected plan/partition bindings, then passed all 28
CPU/CUDA parity checks before training fixed shards 0008–0013. Its first shard
terminal receipt has not yet been observed; these 120 jobs are not counted done.

Local shard 0038 also completed 20 jobs with execute and separate verifier exits
0. Its archive is 61,993,556 bytes, CRC passed, SHA
`ee9886b0c29530bf3c6bcc0c986c1c0d223184eff4742cc5c16849dbbf80cf26`.
Certified whole-shard receipts now cover **122/782 new jobs**; **66** additionally
passed independent remote archive readback. Local archives for 56 jobs remain
on the persistent local SSD awaiting remote publication/readback. Another 660
jobs remain outside completed-shard certification: 160 local, 120 in current
Kaggle group 03 and 380 in subsequent conditional groups. Running shards may
already contain individual terminal job receipts; this count deliberately uses
complete shard evidence. No job is counted twice.

## Metric/report correction

The [v2 partial report](hung-development-partial-20261027-v2/report.md),
[CSV](hung-development-partial-20261027-v2/paired.csv) and
[JSON](hung-development-partial-20261027-v2/summary.json) supersede the earlier
table's transfer terminology. As required by `docs/SPRINT_PLAN.md` and
`docs/MASTER_RESEARCH_FLOW.md`, **transfer gain and negative-transfer rate apply
only to Source-using methods compared with Target-only**. Other method/reference
comparisons retain generic MAE differences and worse-than-reference station
fractions; their NTR is `n/a`, not a transfer claim. Evaluation units still need
independent approval before Final.

This is a reporting/schema correction, not a model/configuration selection or
new result. All **111 per-run metrics and 11 station-first MAE/RMSE/reference/gain
rows are exactly unchanged**. The same pinned snapshot remains 69 reused Main
plus 42 local new runs: 60 scorable and 51 with no scored horizons. Newly finished
shard 0038 and Kaggle results are outside that metric snapshot. Earlier reports
and generated files remain intact. Corrected result schema is
`hung-development-partial-results-v2`, SHA
`95d63a6adf8b8c4e5b2f7c08b131defdd892953b3d0628ef672e554d170ca584`.

The scorer's optional-NumPy dependency was also removed after Linux CI exposed
it. Original-unit label hashes now use standard-library little-endian float64
packing. Actual 111-run recomputation before and after that backend change
produced identical full JSON SHA
`56e9370abafbc1e155c7f2f9e06ad5848025c157f5018a0afe88d58b7bd4010d`.
Linux CI passed at fix commit `5b175d2`; the local clean-commit full suite passed
**306 tests, one skip, exit 0**, in 219.525 test seconds. The subsequent reference
semantics change passed nine focused tests and another real 111-run integration,
including equality checks against all earlier numeric rows. Full Ruff
check/format and diff checks pass; later CI status is reported separately.

[Evidence JSON](evidence/hung-development-group03-metrics-v2-20261027.json)
records both complete group-02 receipts, independent readback, local receipt,
GPU parity, source/log hashes and test terminals. Changed files: scorer, report
formatter, result tests, the three new v2 generated report files and this report
with its JSON evidence. Commands: result scoring/report CLIs, focused unit tests,
full offline discovery for the NumPy fix, full Ruff and `git diff --check`.
No checkpoint, historical identity or model code changed; execution remains
`44b8532`. Reviewer Kaggle usernames are still needed for private artifact
access. Full matrix coverage, independent review, #39 substitution approval and
an immutable Final lock remain open. No Final evaluation, merge or issue closure
occurred.
