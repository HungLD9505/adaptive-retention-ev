# Main/local review capsule: independent readback — 2026-10-27

The [private review Dataset, version 1](https://www.kaggle.com/datasets/hungluongduc/hung-review-capsule-20261027-v1/versions/1)
now preserves **69 historical VERIFIED_REUSE Main runs plus 56 completed local
jobs** from shards 0039, 0037 and 0038. The capsule is 281,065,935 bytes, SHA
`2493e0c1f440f6b5ead7c81facb3901623c4a58252ca7fa656cf9bdb1e32953d`.
All run IDs, manifests, checkpoint/event-journal bytes, code provenance and
Source/Target identities remain unchanged. Historical unmatched Block-7 is not
included. Selection used ledger readiness and complete fixed shards, never MAE.

[Independent Kaggle CPU version 362641156](https://www.kaggle.com/code/hungluongduc/hung-review-capsule-cpu-readback-20261027-v1?scriptVersionId=362641156)
actually mounted that Dataset, verified the complete capsule SHA/CRC and file
inventory, checked all historical Main pins and local nested-archive job/stage
receipts, and recomputed saved live-forecast metrics for **125 runs**. It passed
in **19.251 verification seconds**, **36.9 whole-provider seconds**, Python
3.13.15 / Torch 2.11.0+cpu. There were **64 scorable runs and 61 with zero scored
horizons**. Missing labels remain missing; no training, configuration selection
or Final evaluation occurred. No model package checkout was needed for scoring.
The verifier's peak RSS was not instrumented and is not inferred; this stage
used CPU, zero GPU training time and zero model updates.

The Dataset's verifier source SHA is
`78c4bd421ec0971023dca141ed8e81b22dbc97fe5c5855cd2511bfb30d1761be`.
The standalone scorer is itself pinned inside the capsule; only its CLI writer
imports the model-package receipt utility. Tests explicitly verify that scoring
works with the entire `experiments` package unavailable. This proves stored
checkpoint/forecast readability and original-unit metric reproduction across
the local Torch 2.8 and provider Torch 2.11 environments. It does not claim full
cross-version training-trajectory parity or non-author scientific approval.

[Machine-readable evidence](evidence/hung-review-capsule-readback-20261027.json)
contains the archive receipt, code/plan/partition/scorer pins, exact local input
paths, remote summary, source/log hashes and test terminal. Original data and
archives remain intact. GitHub receives only code, the thin notebook and small
report/hash metadata; the capsule/checkpoints stay in private storage.

## Workload and gates

Local shard 0029 separately completed another 20 jobs with verifier exit 0 and
archive CRC passed. It is outside this capsule and still needs remote readback.
Complete-shard evidence now certifies **142/782 new jobs**, with **122** verified
by remote readback. The 69 historical Main copies are not added to either new-job
count. Another **640** jobs remain outside completed-shard certification: 140
local and 500 Kaggle. The existing Python GPU/CPU workers continue; partially
completed running shards are not included in these totals.

The local clean-commit suite passed **311 tests, one skip, exit 0**, in 213.137
test seconds / 220.294 wrapper seconds. Windows and Ubuntu CI both passed at
`ed040c2`. Focused archive tests cover corrupt bytes, missing members despite
valid ZIP CRC, unsafe paths and overwrite refusal; the actual local 125-run
readback and the separate provider readback both passed. Full Ruff check/format
and diff checks pass. Dataset visibility was explicitly Private; the owner UI
showed 5.89 GB used of 214.75 GB private quota before this upload. That is a
storage observation, not a current GPU quota estimate.

Changed files: `tools/hung_review_capsule.py`, `tools/hung_results.py`,
`tests/test_hung_review_capsule.py`, `tests/test_hung_results.py`,
`experiments/hung_sprint2/kaggle_review_capsule_v1.ipynb`, this report and its JSON
evidence. Commands: `python -m tools.hung_review_capsule --spec ...` followed by
the same module with `--archive-sha256 ... --score`, focused unit tests,
`python -m unittest discover -s tests -v`, full Ruff check/format and
`git diff --check`. No existing data/checkpoint/report was overwritten.

Reviewer Kaggle usernames are still needed before granting access. #39 remains
open because no independent provider-substitution decision has been recorded.
Full baseline/ablation/budget/seed coverage, remaining archive readbacks,
historical Block-7 fairness, independent review and an immutable Final lock
remain outstanding. A separate CPU readback is technical durability evidence,
not independent peer approval. No PR was merged, issue closed or Final run made.
`docs/SPRINT_PLAN.md` remains the only schedule.
