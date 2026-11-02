# Release verification reference

The offline checker validates packaged report-source hashes, original frozen
source pins, preserved source histories and the absence of tracked large-data/run
storage. It does not authenticate unavailable remote artifacts or rerun experiments.

The [curation verification](release-curation-20261102-v1.json) records a clean
checkout with 911 passed tests and two CUDA skips, Ruff/catalog/release checks,
archive hashes, retained numerical evidence and two existing PDF identities.
Later documentation edits are separate from that recorded test snapshot.
Eighteen external-artifact tests were not run; no new training or PDF compile is
claimed. Full runtime accounting and corrected diagnostic real-data validation
remain limited as stated in [the scope record](../../RELEASE_SCOPE.md).

The original integration/readiness chronology is available in the
[historical snapshot](https://github.com/HungLD9505/adaptive-retention-ev/blob/c8a2afc007bb6e8f739dec219d43ae06f492139c/docs/reports/main-readiness-20261102.md).
