# Persistent controller validation ledger

## GitHub Actions: executed

Execution code: `bd552cf0484fe047ed96416f569cc19529bc4111`.
[Foundation checks run 42855814417](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42855814417).
These are remote fixture tests, not empirical training results or Kaggle outcomes.

| Job | Test command | Observed result |
| --- | --- | --- |
| Ubuntu 24.04, job 129968406722 | `python -m unittest discover -s tests -v` | 945 tests in 84.330 s; OK, 2 skipped |
| Windows, job 129968406012 | `python -m unittest discover -s tests -v` | 945 tests in 171.953 s; OK, 4 skipped |

Both jobs passed dependency installation, `pip check`, and `tools.sources list`.
Ubuntu logs identify Python 3.12.16 and the workflow installs Torch 2.11.0 CPU
and NumPy 2.3.3. The skipped tests remain skipped; this is not a claim that every
optional artifact/GPU check ran.

Both jobs failed `python -m ruff check .` with four I001 import-block findings:
`ev_runner/continuous.py`, `tests/test_issue99_persistent.py`,
`tools/issue99_persistent_experiment.py`, and
`tools/issue99_persistent_notebook.py`. The formatter and final diff checks were
therefore skipped. Commit `f1d02f0` fixes the reported import ordering/spacing;
its eventual CI result must be recorded separately.

CI now prints a formatter diff on failure. The follow-up workflow also fetches
full Git history and runs `tools.check_release` plus both README experiment test
directories remotely, so historical tag verification does not depend on the
limited embedded Kaggle code package. Those added checks are pending execution
at the time of this entry.

## Kaggle: submitted, results pending

Version 2 of the existing paired-comparison notebook was accepted at approximately
2026-11-10 16:33 UTC on T4 x2. See
`issue99-persistent-kaggle-handoff-20261110.md` for commit, package hash and paths.
The notebook runs focused tests before pilot and stops on a required check error.
The CI import findings above also apply to the pinned Kaggle code; if Ruff is
installed there, that technical gate may stop the version before training.
Do not silently patch a running package or reinterpret such a failure as a
completed experiment. Preserve the failed output and issue a new pinned version.

No persistent Calibration or later MAE is available in this ledger yet.

## Expanded README checks at db30221: Ubuntu result

[Run 42857425202](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42857425202),
Ubuntu job `129974280419`, passed `tools.check_release` (17 report files and
92 frozen source files authenticated), 945 main tests in 68.720 seconds,
9 Fixed-adaptation tests in 0.901 seconds, 12 confidence-controller tests in
0.033 seconds, and `ruff check .`. Ruff's formatter reported 10 files needing
formatting; `git diff --check` was skipped after that failure.

The exact formatter patch was read from the remote job log. A first patch
extraction included an interleaved Ruff summary line and `git apply --check`
rejected it as corrupt; no source changed. Removing only that log summary
produced `.cache/ci-db30221-format-v2.patch`, which passed `git apply -p0 --check`
and was applied. These are code edits from remote formatting output, not local
model execution. The newly formatted commit still needs its own CI result.

The audit, report and dispatcher modules exceed 500 lines after formatting.
Their cohesive artifact-verification, reporting and phase-dispatch responsibilities
are disclosed for reviewer agreement; no line-count-only split was performed.

## Full CI at c0ef72c: passed

[GitHub Actions run 42858352451](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42858352451)
completed successfully for commit `c0ef72c` on both Windows and Ubuntu. The run
passed the full registered checks, including the README experiment checks and
Ruff. This is code/fixture validation, not a Kaggle training or MAE result.
The earlier CI failures above remain in the ledger as resolved history.

## Kaggle status update

Version 2, run `368131180`, and Version 3 were cancelled after zero seconds
because the editor held notebook JSON as a Script. **File → Editor Type → Script**
was then explicitly selected, and the saved Version 4 source was inspected as
Python. [Version 4, run 368138679](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2?scriptVersionId=368138679)
is pinned to code commit `087b7ee085835824fc7bb8effef7a05df126e6e8`
and embedded ZIP SHA-256
`dc1e78cf2ba00cf11794b32ed42f140777e904a4a012c6423dc9aa9b497ad0a8`.
It was **Queued** at the last observation. No persistent pilot, Calibration,
Later, metric, or GPU availability result is available yet. The full path and
session details are recorded in `issue99-persistent-kaggle-handoff-20261110.md`.

## Kaggle executed pilot and Calibration (2026-11-11)

The final package at commit `b2ab78b` completed six pilot runs and all 48
Calibration cells under protocol SHA-256
`f0443273e12eac8c0f8311e4e7b7ba2abd7bdc2a616a74d688bea442fcd96acb`.
The output root is `/kaggle/working/issue99-persistent-b2ab78ba`; package
SHA-256 is
`97cf995e84decb5e7725a7e5f5216a1281ae86df49a57e4983dd07e2c6c7faf0`.
The Kaggle runtime recorded Python 3.13.16, Torch 2.11/CUDA 13.0 and T4.

The focused 26 tests passed in 14.36 seconds. The Kaggle environment did not
have Ruff installed, and the small embedded package did not contain the README
files for `check_release`; therefore those two checks did not pass inside this
Kaggle run. The full Windows and Ubuntu CI at `c0ef72c` separately passed
Ruff and all README checks in run `42858352451`. No local model execution is
claimed.

Independent saved-vector/arrived-label verification reported **PASS** for the
executed matrix. The registered Calibration gate reported **FAIL**, with
Persistent macro MAE `5.331587155372982` kWh versus Fixed
`5.331705633298364` kWh: improvement `0.00011847792538244306` kWh, below
the required `0.01` kWh. The Persistent/Fixed wall ratio was
`1.6138442882175836`; only seed 42 improved at the seed macro level. Pilot
accepted no candidate blocks, leaving the real trajectory equal to Fixed.
Only target 1153/seed 42 ended Calibration with λ `0.898445` rather than
`0.798445`; the others remained at the initial value. The gate therefore
prohibited Later execution; no Later MAE exists for this package.

The 12 historical Fixed Calibration cell deltas and the Fixed and immediate
macro deltas were reported as zero against the new runs. The failed interactive
`087b7ee` package (missing `ev_baselines`) and `3c6b3c7` package (protocol
trailing comma) stopped before training, and are packaging errors, not
empirical controller outcomes. The earlier queued Version 4 was cancelled for
interactive use. Full result tables and artifact hashes belong in the separate
main results report, not this validation ledger.
