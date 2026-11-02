# Block7/Main origin event eligibility audit — 28 October 2026

This read-only audit extends the [69-cell manifest pair table](hung-block7-manifest-pairs-20261028.md) for Qyroven's [PR #68](https://github.com/HungLD9505/adaptive-retention-ev/pull/68) and [PR #70](https://github.com/HungLD9505/adaptive-retention-ev/pull/70) review requests. The [new 69-row table](hung-block7-origin-eligibility-20261028-v3.csv) retains historical and Main run IDs, their pinned manifest/event-journal SHA-256 values, per-run event-schedule SHA-256 and `PENDING_PEER` status. It does not relabel a historical run or select a method by its metric. Two preliminary CSVs remain unchanged in this isolated worktree and are not published as evidence; v3 uses stable LF line endings for exact Git byte preservation.

The read-only [generator](../../tools/hung_block7_origin_events.py) rehashed the 121,893-byte original coverage copy against its committed coverage-audit pin (`52e39a8330c929aa44cc1df21fdbc257a0ad74bfadddb4e3aa3b0da04697631a`). It then rehashed all 138 copied run manifests against the frozen coverage record. Within each manifest, it validated 90 requested origin events, exactly one `forecast` or `skip` tag per origin, 90 `unscored` event tags, the recorded scored/skipped counts, and matching `score`/`update` origin lists. An `unscored` tag can coexist with a later score for the same origin when a label arrives; it is **not** interpreted as a zero metric or final proof of a missing label. The ordered timestamp lists for `forecast`, `skip`, `unscored`, `score` and `update` match in **69/69** Block7/Main pairs: 18/18 at 7 days, 24/24 at 14 days and 27/27 at 28 days. The v3 CSV SHA-256 is `2a025850fa4e363db173833ea6aa4b9a40b4bccc1dd0e545715984505e283955`.

This checks only the hashed **manifest summaries** of origin event tags. The original event-journal bytes were not reopened here, and the two block lengths legitimately change decision/audit-update cadence. Therefore equal origin tags do not prove equal forecast values, labels at every update, RNG trajectories, controller state or a numeric tolerance. The earlier audit's 9/9 Source and 69/69 Target payload-equality counts remain prior evidence rather than a fresh checkpoint comparison by this worker.

I searched only the current repository cache for paired checkpoint bytes. All 391 local `.pt` files (about 0.15 GiB) were streamed through SHA-256 and compared with the 9 unique historical Source, 69 historical Target, 9 Main Source and 69 Main Target file hashes in the pinned pair table. The current cache contains **0/9 historical Source and 0/69 historical Target** matches, versus **9/9 Main Source and 69/69 Main Target** matches. The historical paired checkpoint bytes are therefore unavailable **in this repository cache** for a fresh model/optimizer/scale/RNG payload audit. This does not contradict the earlier PR #70 comparison performed in another worktree, and it is not proof that those historical artifacts do not exist elsewhere. No outside-repository file was accessed.

## Reproduce and remaining review

With the ignored original coverage copy and 138 pinned manifest copies available inside the repository, run:

```sh
python -m tools.hung_block7_origin_events --coverage .cache/block7-review-v1/coverage.json --manifest-dir .cache/block7-review-v1/manifests
python -m unittest tests.test_hung_block7_origin_events -v
python -m ruff check tools/hung_block7_origin_events.py tests/test_hung_block7_origin_events.py
python -m ruff format --check tools/hung_block7_origin_events.py tests/test_hung_block7_origin_events.py
```

The output command is create-only or checks byte identity if the table already exists. A changed coverage or manifest hash fails closed. A fresh paired checkpoint review requires exact historical `.pt` bytes or the prior byte-pinned comparison proof, plus per-origin forecast/label/journal comparison and a declared numeric tolerance. A non-author reviewer then decides whether 69 historical runs may be mapped as equivalent or 69 new replay IDs are needed. Until then, all 69 remain `PENDING_PEER`; no replay, training or Final job was run.

**Checks here:** the generator produced 69 rows and 69 equal origin-tag schedules; a second invocation confirmed byte-identical v3 output. Four focused offline tests passed, as did Ruff lint/format for the two new Python files and `git diff --check`. The installed Python did not expose `ruff` as a module, so the repository-cached `.cache/local-tools/bin/ruff.exe` was used for the actual lint/format checks. The full suite was not rerun for this bounded evidence-only addition.
