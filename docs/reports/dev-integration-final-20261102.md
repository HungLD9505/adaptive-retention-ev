# Dev integration scope and handoff — 2 November 2026

Related: #15, #19–#23, #39–#41, PR #76. This record supersedes the stage-one
handoff for the combined integration scope; it does not rewrite historical runs.

## Lead authorization

The human lead explicitly instructed scope selection, bug fixing, refactoring and
integration without waiting for another reviewer, acting as advisor. This overrides
the usual non-author approval condition **for this dev integration**. The preceding
explicit CI waiver also applies because GitHub billing/spending capacity is exhausted.
Record both as lead-directed exceptions, never as independent scientific approval
or successful remote CI. Main promotion is outside this change.

## Accepted repository scope

- The Qyroven packages are the primary report pipeline; their scientific code/config
  and the frozen Final lock remain unchanged by the integration.
- Hùng's #72 implementation and evidence are preserved as a separate supporting
  track, with original author history. Its bounded three-station Final is not the
  primary 810-unit Final, and unresolved scientific lineage/parity/scope gates remain
  limitations. Integration does not declare those experiments independently approved.
- Đức/Cyber remain isolated member studies. Historical scores are preserved and are
  not pooled. Cyber input/replay fixes are a new guarded IO version with no new
  training evidence; the earlier scores are not relabeled as corrected results.
- Other side branches with unique changes remain preserved pending their specific
  disposition. This is not a blanket merge or deletion of all 37 original branches.

## Engineering changes

The Hùng merge had three conflicts: README, root model requirements and CI install
steps. The primary Python/PyTorch/NumPy environment remains the root default; Hùng's
original CPU requirement is preserved in `experiments/hung_sprint2/requirements-reference.txt`.
This does not claim numeric equivalence to his historical runtime.

The Cyber runner is refactored by responsibility into input adaptation, execution
and CLI modules. The adapter reuses authenticated input and availability contracts;
no member model weights are shared. It rejects invalid roles/prefixes/scalers,
requires explicit manifest pins, writes/flushed/syncs forecasts before label access,
skips incomplete labels, rejects late labels before update, requires complete
calendar blocks and creates a new output directory instead of overwriting evidence.
The bounded study explicitly rejects configured delayed-label profiles; general
pending-delay execution belongs to the primary runner. Original model/loss/controller
conventions remain distinct and unchanged.

Fresh integration initially ran 891 root-discovery tests and reproduced 16 errors,
two failures and two skips. All 18 failing/error cases require historical files or
pinned source staged in ignored `.cache` locations. They are preserved, with unchanged
assertions/hashes, under `tests/artifact/` and run explicitly after artifact restoration.
Synthetic regressions stay in default offline discovery. A later dirty-worktree run correctly failed a calibration fixture that rejects dirty code; final verification is therefore performed from a committed clean checkout, without relaxing that guard. Seven new IO regressions
cover prediction persistence before labels, incomplete/pending labels, nonfinite Y,
no overwrite before adaptation, explicit delay/partial-block rejection and manifest
pins. Fixture-only temporary-file tests no longer require a pre-existing cache folder. Ruff also normalizes import spacing in two Hùng diagnostic scripts; their Python ASTs are unchanged.

## Verification and limits

Final local and clean-checkout verification is recorded in the companion JSON after
execution. External-artifact tests have not passed here: their required real artifacts
were not restored. No raw archive edits, new real-data training, Final replay, billing
changes or main promotion are part of this integration. Original local outputs and
uncommitted reports were backed up and preserved during stage one.

The original generated AMS SVG retains its historical bytes and trailing whitespace;
full PR-range whitespace checking flags that known inherited artifact. New integration
edits must pass diff checking. This is not described as a clean full-range result.
