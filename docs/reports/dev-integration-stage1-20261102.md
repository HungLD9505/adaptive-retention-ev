# Dev integration stage 1 — 2 November 2026

Related issues: #15, #19–#23, #40 and #41. This branch is a concrete integration
candidate targeting `dev`, not an accepted release or a full-repository completion.
The [machine-readable record](dev-integration-stage1-20261102-v1.json) pins heads,
checks, frozen-file hashes, backup identity and outstanding scope.

## Authorization and status

The user requested integration preparation and explicitly waived waiting for GitHub
CI because billing/spending capacity is exhausted. Record CI as **NOT RUN / user
waiver**, never as passed. No billing settings, purchases or workflow protections
were changed. No remote dev/main update, branch deletion or issue closure is part
of this stage. Non-author approval on the final head is still absent; no approval
is fabricated or inferred from the CI waiver.

## Included work and conflict resolution

- Merge-preserve #52 and therefore its exact #47/#49/#50/#51 dependency heads.
  No primary scientific Python, configuration, input policy or runtime tool was
  changed from #52 by this stage.
- Merge-preserve #69 (Duc) and #48 (Cyber) with their original authored commits.
  Member implementations remain isolated and their metrics are not pooled.
- Merge-preserve #75. Its README conflict with #52 was resolved by using completed
  Final evidence while retaining implementation contracts and run instructions.
  The README explicitly labels this as a candidate, not integrated dev acceptance.
- Preserve the local 31 October post-hoc analysis, full-precision JSON and Report 1
  manuscript review. These are editorial/descriptive evidence, not new training.
  The manuscript review references historical local `output/paper-v6` artifacts;
  those paths are not included in this source checkout or claimed portable.
- Add the branch/PR/issue inventory and this integration handoff. Raw data, large
  runs, checkpoints, local manuscript builds and environments remain outside Git.
- Add a Cyber study README identifying source-reviewed availability/input guards,
  missing persisted forecasts, repeated-run overwrite behavior and differing
  source-scale conventions. Preserve the historical source and scores unchanged;
  passing model/controller fixtures does not accept its prequential replay.

## Local verification

Fresh isolated Python 3.12.13 / PyTorch 2.11.0 / NumPy 2.3.3 environment on macOS
arm64 CPU; Ruff 0.17.0 matches `requirements-dev.txt`.

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -v` | 406 tests, OK |
| `python -m unittest discover -s experiments/member_studies/duc_retention -v` | 9 tests, OK |
| `python -m unittest discover -s experiments/member_studies/cyber_controller -v` | 12 tests, OK |
| `python -m tools.sources list` | Exit 0; reads catalog only, no fresh archive verification |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 243 files already formatted |
| `uv pip check --python <isolated-python>` | Installed package dependencies compatible |
| Primary-code/config comparison against #52 | No differences in primary packages, tools, configs or source catalog |
| Frozen lock tracked file pins | 92/92 bytes/SHA matched; 48 external `runs/` paths absent in this checkout |
| Working-tree `git diff --check` | Passed for new integration edits |
| Full PR-range `git diff origin/dev...HEAD --check` | Flags trailing whitespace in the inherited generated AMS SVG; original evidence bytes preserved, not a clean PR-range pass |
| Exact dependency/member/synthesis head ancestry | All 8 named PR heads preserved |
| Backup of original worktree uncommitted work | 587 files; archived bytes rehashed against originals |

Member dependency-specific fixture tests run separately because root discovery does
not cover those directories. The integration environment is not the historical
Duc training environment (whose separate requirements remain unchanged); these
fixture results do not establish numerical training parity. No GPU, provider access,
real-data training or new Final replay was run. The original worktree and artifacts
remain untouched. Full external artifact verification is not claimed.

## Remaining scope and attribution

The current candidate preserves three member identities: Qyroven, huuduc32 and
hung00cyber. Hùng's #72 supporting stack is intentionally not imported before its
latest-head correctness review and the unique side branches are reconciled. The
[repository audit](repo-integration-audit-20261102.md) lists every disposition.
The all-four-contributor requirement remains a prerequisite for later main
promotion; this stage does not claim to satisfy it yet.

Do not close the component issues or delete their source branches merely because
their commits appear in this candidate. After review, select one accepted integration
route, verify preserved work and attribution on dev, and only then perform cleanup.
No main promotion is requested by this stage.
