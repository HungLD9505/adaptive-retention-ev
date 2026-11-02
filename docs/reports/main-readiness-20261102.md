# Main candidate handoff — 2 November 2026

Related #15, #23, #39, #40 and #41. This handoff prepares a concrete dev snapshot
for a separate main-promotion decision; it does not promote main.

## Scope decisions

[RELEASE_SCOPE.md](../../RELEASE_SCOPE.md) is the current inclusion/limitation record.
The four remaining research/member acceptance gaps are retired as **not planned**
for this bounded report release, not marked as successful experiments or completed
artifact delivery. #15 remains the release gate. The historical issue bodies and
all adverse/null evidence stay preserved.

This consolidates a research repository, rather than cherry-picking a different
method or cohort because it has more favorable scores. The primary pipeline, Hùng
supporting implementation and member studies retain different identities. Source
heads from all four members must be ancestors of the candidate; GitHub profile/UI
attribution is checked separately after main promotion/cache refresh.

## Refactoring and checks

The maintained README is reorganized around the report, supported commands, core
packages, provenance and limitations. Historical reports stay dated evidence, not
current run instructions. A stdlib-only release checker validates the packaged
report, original scientific source/tag and four-member source-head reachability.
It rejects changed report assets, duplicate/escaping/symlinked inventory entries and
tracked raw/generated storage. It requires no PyTorch, GPU, credentials or network.

Fixture tests use the standard SHA-256 vector for ASCII abc, changed bytes, duplicate
or empty inventories and external path/symlink cases. They test packaging boundaries,
not scientific effectiveness. Full clean-checkout checks and the candidate SHA are
recorded after execution; later documentation-only changes are distinguished from
the tested code. No actual real-data training or missing-artifact verification is
performed for release preparation.

## Verified candidate

Code commit `b751d491272fa9964ffd74b8bdc9a0051bb6070b` was tested in a fresh shared Git clone
with a clean tracked checkout before and after checks. Root discovery ran
892 tests, with two CUDA skips; Đức ran 9 and Cyber ran 12.
Total: **911 passed, 2 skipped**. Ruff lint and format (870 Python files),
source catalog listing, release provenance checks and this change's whitespace
check passed. Expected negative-fixture diagnostics are not suite failures.

The [machine-readable verification](main-readiness-20261102-v1.json) records the
environment, log hashes and limitations. Eighteen external-artifact tests were not
run. No fresh training, PDF compilation, remote CI pass or independent approval is
claimed. Subsequent edits in this PR are documentation-only. Main remains unchanged.

The complete main candidate includes the earlier integrated implementations and
17 byte-identical report assets. Vendor/template whitespace already preserved in
that history means a full main-to-dev whitespace check is not clean; this change
does not rewrite the original report source to conceal it. All four original
member source heads remain ancestors; GitHub contributor-profile visibility on the
default branch is not established before promotion.
