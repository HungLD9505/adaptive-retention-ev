# Partial metric recomputation and per-shard storage gate — 2026-10-27

The CPU scorer actually rehashed and recomputed **111 runs**: 69 historical Main
runs marked `VERIFIED_REUSE` by the pinned G0 ledger and 42 completed local jobs.
**60 have scored horizons; 51 have zero scored horizons.** Among the 42 new local
jobs these counts are 24 and 18 respectively. Missing labels remain missing;
successful training is not evidence that a run has a usable evaluation metric.
The other 20 completed Kaggle jobs are outside this local metric snapshot.
The total completed-new-job count remains 62/782, not 111/782.

[Generated Markdown](hung-development-partial-20261027/report.md),
[paired CSV](hung-development-partial-20261027/paired.csv) and
[small JSON summary](hung-development-partial-20261027/summary.json) retain method,
budget, station/seed coverage, gains and negative-transfer counts. The full local
result JSON SHA is
`56e9370abafbc1e155c7f2f9e06ad5848025c157f5018a0afe88d58b7bd4010d`;
the SHA-pinned catalog is
`2d4b3aa5284552a0b82955ab5e05cdc2832f96a06a24145a1d0a7f3c2dd67da8`.
Large checkpoint/forecast files and the full local result JSON are not committed.

## Scoring and fairness

For each issued Development forecast, the scorer uses only complete, already
arrived labels saved in its runner checkpoint. Predictions and labels are
converted back to original kWh with that checkpoint's immutable energy scale.
For D complete paired days, MAE is `sum(abs(prediction-label))/(24*D)` and RMSE
is `sqrt(sum((prediction-label)^2)/(24*D))`; daily RMSEs are not averaged.
Candidate/audit losses do not replace the actual live-policy prediction.

Every checkpoint and manifest is hashed against its pinned catalog. Catalog
construction rechecks complete job/stage receipts, config, input identity and
all inventoried stage files. Historical Main uses its G0 manifest, checkpoint,
Source/Target and event-journal pins. Seeds and station/budget bindings must
agree. Comparison cells require the same input identity, equal Source/Target
hashes where both methods use those initializers, and equal original-unit label
bytes on the intersection of scored day IDs. A single-policy baseline's seed
comes from its plan-bound stage/job receipts; its manifest does not expose a
separate seed field. This is not treated as an absent or invented seed.

Within each budget, errors are computed per paired station/seed; seeds are
averaged within station, then stations receive equal weight. Budgets remain
separate. Absolute MAE gain is reference MAE minus method MAE; relative gain
divides that difference by reference MAE and is undefined for zero reference
MAE. Negative transfer is the fraction of stations whose seed-mean MAE exceeds
their paired reference. Pairwise tables can use different cohorts and do not
form a global ranking. Some rows have only one seed/station; none establish
complete baseline/ablation coverage or select a configuration. The snapshot
contains 18 blocked pairs with no paired scored days. Historical unmatched
Block-7 is excluded, without relabelling or retraining old runs.

## Storage correction before subsequent GPU groups

The initial CPU coordinator was deliberately stopped before submitting group 03.
The authenticated status API returned `CANCEL_ACKNOWLEDGED` for version 362629668.
The old group-03 lookup returned 403; that endpoint was not retried. Its ordinary
owner-facing page reports “We can't find that page.” No old group-03 submission
was observed in the coordinator's flushed log. Existing GPU group 02 and the
local worker continue independently; their running jobs are not counted complete.

The correction makes every subsequent shard upload its archive plus receipt to
a **create-only private Dataset**, preserving the ZIP as `artifacts.zip.bin`.
It then submits a separate CPU version with that exact Dataset version attached.
The CPU process must read the exact receipt, hash all archive bytes, check CRC,
the canonical job-set digest and expected relocated plan/partition hashes, and
exit successfully before the GPU process may start another shard. Upload alone
cannot produce a `VERIFIED` durability receipt. Conflict, timeout, partial data
or a failed readback stops execution and preserves evidence. Dataset creation
never falls back to a new version.

A CPU-only integration is testing this path with the actual completed
65,931,034-byte shard-0001 archive; it does not rerun its 20 training jobs.
The v2 coordinator uses separate provider/control identities, the same immutable
allocation and model code `44b8532`, and still waits for the existing group 02.
Its execution is conditional on the real integration result; preparation is
not a claim that the remaining 500 jobs have run. Per-shard Dataset persistence
removes dependence on all six shards in a larger group finishing before their
archives become durable.

## Files, commands and remaining gates

New maintained files: `tools/hung_results.py`, `tools/hung_result_report.py`,
`tools/hung_kaggle_storage.py`, their result/storage tests, the v2 CPU coordinator
notebook, this report and the three small generated result files. The existing
`tools/hung_kaggle_queue.py` gains the per-shard storage barrier and v2 identities.
The v1 notebook and all earlier reports remain preserved.

Commands: `python -m tools.hung_results --build-catalog ...`,
`python -m tools.hung_results ...`, `python -m tools.hung_result_report ...`,
the focused result/queue/storage unit tests, full-repository Ruff check/format
and `git diff --check`. Actual 111-run scoring completed with exit 0 and all
declared metrics matched independent saved-forecast recomputation at 1e-9
relative/absolute tolerance. Eighteen focused tests pass; the earlier full suite
passed 295 tests / one skip. An enlarged clean-commit full run is still required.

Unfinished: the remaining Development jobs and archive readbacks, complete
9-baseline/5-ablation/three-budget/three-seed comparison coverage, independent
fairness/reproduction review and the #39 provider-substitution decision. Only
after those gates and an independent immutable lock may Final run and #10's
final Results/Discussion/Limitations be completed. No merge, issue closure or
Final-label access occurred. `docs/SPRINT_PLAN.md` remains the sole schedule.
