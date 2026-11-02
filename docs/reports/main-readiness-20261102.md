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
