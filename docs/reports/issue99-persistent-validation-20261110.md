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
