# JSONL audit and numerical-win review supplement

Resolves the two follow-ups in
[HungLD9505's review](https://github.com/HungLD9505/adaptive-retention-ev/pull/120#issuecomment-6848388835).
Issue #121; depends on #120. No locked cohort, primary result or acceptance rule
is changed.

## Original audit boundary

`original-ref-jsonl.json` enumerates all five JSONL blobs reachable from the exact
commit IDs in the original audit's 107 refs. It includes JSONL anywhere in the
repository, not only the current tree. Byte hashes, Git object IDs, paths and
structured target declarations are retained. Two execution/event logs identify
only UrbanEV 1405, 2152, 1153 and 1693. Three historical CHARGED archive readbacks
contain download names, sizes, hashes and verification timestamps, not target
identity declarations. No selected cohort ID occurs as a target declaration.
Raw digit-token matches in those five files arise in timestamps, numeric metrics,
byte sizes and hashes; they are not interpreted as target uses. This is a
retrospective extension to a bounded recorded-use audit, not universal exposure
certification.

The scanner now supports multi-record JSONL, conservative execution identities
and the published baseline run-ID representation. Malformed JSONL objects,
truncated records and invalid UTF-8 fail rather than disappearing silently.
Regression tests cover these cases. Prepared artifacts under `data/inputs` are
classified separately and not opened by the corrected local metadata scanner.
The original execution's pinned scanner bytes remain recoverable at `6ef963d`;
its lock and original receipts are not rewritten to match this newer scanner.

## Expanded local audit and preserved attempt

`current-history-audit.json` records the corrected expanded audit, including the
paths of prepared artifacts deliberately not opened. Full scan manifests and
reference-bearing exclusions remain under the external issue121 run root.

The first local extension attempt traversed prepared-input copies before its
path filter was corrected. Preserve that attempt as `current-history-v1`;
it is not a valid metadata-only cohort preflight. `additional-exposure.json`
records the affected value files and **249 identifiers**, including Source IDs.
Their values did not enter candidate ranking or model training, but all such
identifiers are conservatively ineligible for any subsequent new-ID claim.
The second audit skips these prepared arrays; the additional-exposure exclusion
set must still accompany it. No prior confirmation ID/result is replaced.

## Practical-win interpretation

The original strict-sign count remains **35/46** lower MAEs against Fixed.
Four wins are AMS IDs 1889, 617, 2366 and 1733. Each difference is approximately
**1.4339354e-9 kWh**, so these are numerical-scale differences rather than
practical improvements. A posthoc absolute tolerance of 1e-6 kWh gives **31/46**
gains against Fixed and **28/46** against static. A separate descriptive 0.01 kWh
tolerance gives 27/46 and 16/46. Neither tolerance is a prespecified clinical,
operational or statistical threshold; neither changes the locked mean, interval,
coverage or failed dual-comparator criterion.

`practical-win-diagnostic.json` preserves all counts. The manuscript and original
handoff now state the negligible-win caveat. No effectiveness claim is upgraded.

## Reproduce

```sh
python -m tools.jsonl_history_supplement --repository . \
  --prior-audit docs/reports/issue119-confirmation-20261113/history-audit.json \
  --protocol configs/issue119/new-entity-confirmation-lock-v1.json \
  --output /new/path/jsonl-supplement.json
python -m tools.data_use_history --repository . \
  --local-runs /external/TFL-EV/runs --output /new/path/history
```

Retain the additional-exposure exclusions above when selecting any later cohort.
The fresh audit's post-lock references naturally contain issue119's own target
execution; they cannot be used to retrospectively label that execution prior use.
No comment or review approval is fabricated. Peer review is still required.
