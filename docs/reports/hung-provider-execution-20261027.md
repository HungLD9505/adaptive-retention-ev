# Hung Development provider execution — 2026-10-27

The predeclared six-job local CUDA pilot completed 14 stages with exit code 0
in 331.477 seconds. A separate CPU receipt/dependency verification completed with
exit code 0 in 82.164 seconds. These are technical execution results, not peer
acceptance or evidence of research effectiveness. The remaining matrix is incomplete.

## Identity and actual measurements

The model/dispatcher code remains `44b8532959d76fb20691881539f991ca44983727`
from [PR #70](https://github.com/HungLD9505/adaptive-retention-ev/pull/70).
The immutable 782-job plan SHA is
`2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee`;
the complete disjoint partition SHA is
`7dd340b84a51abca9dcb2e83490d088c07178ffbdbb9d81d68225d665a279c7f`.
Full configuration, input, Source/Target, receipt and measurement pins are in the
[machine-readable pilot evidence](evidence/hung-development-local-pilot-20261027.json).

Pilot selection preceded performance scoring: one seasonal baseline, target-only,
frozen Source, online-best, uncertainty and parameter-retention job, seed 7,
across 7/14/28-day histories. Nothing was selected by MAE/RMSE. CPU/CUDA forward,
latent, losses, gradients and one Adam update passed all 28 checks with
`atol=1e-5, rtol=1e-4`; maximum absolute difference was `3.3974647521972656e-6`.
The first parity harness shared optimizer tensors between devices and failed its
update comparison; the corrected harness deep-copies optimizer state. Both records
are preserved; no model checkpoint was overwritten.

The local device was an RTX 3050 Ti Laptop GPU, Torch `2.8.0+cu126`.
Summed stage subprocess time was 179.561 seconds, local hash/readback time
0.282 seconds. The 331.477-second total also includes orchestration and dependency
verification. Per-stage memory and output-byte measurements, and a nearest-rank
P95 of six per-job subprocess sums, are recorded in the JSON. This small,
heterogeneous sample does not establish Kaggle throughput.

The local pilot ZIP is 101,854,497 bytes, 485 members, CRC passed, SHA
`c567611587a247a29ba72ad01cfe700c8296c2609126d117a634609c5c26e833`.
Remote output upload/readback and independent teammate acceptance remain pending.

## Portable provider execution

`tools/hung_provider.py` packages the pinned Git bundle, exact accepted input ZIP,
78 unique dependency checkpoints and their manifests, configs, selection, parent
plan and complete partition. SHA validation precedes use. Relocation changes only
paths and the resulting plan/partition hashes; job IDs, bytes, seeds and schedules
remain unchanged. A restored checkout stays clean at the original model code SHA.
ZIP traversal, duplicate members, corrupt transport, existing destinations and a
request to repeat completed `pilot_0000` are rejected.

The [private Kaggle payload dataset](https://www.kaggle.com/datasets/hungluongduc/hung-matched-payload-44b8532-20261027-v1)
contains `provider-payload.zip.bin` (149,838,818 bytes, SHA
`23a6d420523d990d07ff07d814ed642a851925283a102a3ae806f3b666e1d6f4`),
the stdlib launcher (SHA
`cadcd80d671d3b49a317312f125735362ffba3068247f1714a0ae56c6be83424`)
and transport metadata. The launcher independently verified the provider-mounted
transport SHA before cloning code and extracting inputs. This verifies input
transport, not durability of training outputs.

The user explicitly authorized Kaggle/local Development execution in this session.
The bounded assignment is `shard_0001` (20 jobs) on Kaggle and `shard_0039`
(16 disjoint jobs) on local CUDA; completed `pilot_0000` is excluded.
Remaining shards are not automatically enabled. The
[private Kaggle version 362612528](https://www.kaggle.com/code/hungluongduc/hung-matched-shard0001-44b8532-20261027?scriptVersionId=362612528)
was observed running on GPU T4 x2, with a Tesla T4, 15,636,037,632 bytes device
memory and 17,988,898,816 bytes free disk. The account UI showed 23h57m GPU
remaining before launch. Quota must be checked again before further allocation.
Only device 0 is used; this launcher does not claim distributed training.

Kaggle's current image provides Torch `2.11.0+cu128`, Python 3.13.15. Its bounded
CPU/CUDA parity probe passed 28 checks. Cross-version comparison against the local
Torch 2.8 reference remains pending; do not call that probe a cross-version test.
The version's completed job count, terminal exit code, output SHA/CRC and independent
readback have not yet been certified by this snapshot.

## Validation, files and outstanding gates

New maintained files are `tools/hung_provider.py`, `tests/test_hung_provider.py`,
`experiments/hung_sprint2/kaggle_matched_shard0001.ipynb`, this report and its evidence
JSON. Existing model and dispatcher source files are unchanged.

Commands completed: `python -m unittest tests.test_hung_provider -v` (5 passed),
Ruff check/format, `git diff --check`, package/materialize, and a restored
`dispatch_matched --shard-id shard_0001` dry-run (20 jobs / 40 stages, exit 0).
The prior full dry-run remains 782 jobs / 1,909 stages, exit 0; prior offline suite
277 tests passed with one skip, as recorded in PR #70. The launcher notebook code
is saved in Git; its imported Kaggle representation is a Python script.

Two preparation failures were corrected and their ignored outputs retained: Git
cannot bundle a bare SHA without a named ref, and relative restored paths needed
normalization to absolute paths. The first package/restore attempts are not success
evidence. Ruff was invoked through the existing project-local executable because
the global Python environment has no Ruff module.

Pending: remaining Development execution; completed output archives and remote
readback; cross-version numerical check; station-first paired metric/coverage and
negative-transfer aggregation; independent fairness/peer review; the recorded #39
provider substitution decision; independent immutable Final lock. Historical
Block-7 identities remain unmatched. No Final selection/evaluation, merge, issue
closure or main promotion occurred. `docs/SPRINT_PLAN.md` remains the only schedule.
