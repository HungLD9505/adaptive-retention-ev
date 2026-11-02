# Block7/Main shared saved-journal event ordering — 30 October 2026

The [create-only 69-pair audit](hung-block7-shared-event-order-20261030-v1.json), SHA-256 `3ed2d544f6cc82bb8f0ac5ff2850432965b52bc8319a827ce8f0acd4f9917b079`, reuses the 138/138 exact-SHA `replay-90` saved journal segments. All 69 pairs have a shared first Main journal day. The comparison applies one fixed boundary rule to **every** pair: omit that first Main day from the core event-order comparison because a resumed journal can begin after some events on that day. It also reports `audit-update` separately because that is the isolated old-policy audit branch, not the live forecast/score/update stream.

| Check | Result |
| --- | ---: |
| Dates present in both saved segments | 3,348 |
| Full ordered tag differences | 196 |
| Differences only in `audit-update` | 160 |
| Core-tag differences on the first Main saved day | 36 |
| Nonboundary shared dates compared for core tags | 3,279 |
| Core-tag order differences on those nonboundary dates | **0** |

Core tags are `forecast`, `skip`, `score`, `unscored` and `update`, in their observed order within each day. The JSON retains each pair's denominator and difference classification. Reproduce with `python -m tools.hung_block7_shared_event_order_v1`; the tests ensure a changed interior core order is detected and a boundary difference is classified separately.

This is stronger evidence of **shared core event ordering on the observed saved suffixes**. It does not show equality of numeric forecasts, optimizer updates, bootstrap draws, events before the respective resume checkpoints, or equivalence of 7- versus 14-day policy outcomes. The 160 audit-branch differences are reported rather than erased. The independent reviewer must still decide historical Block7 fairness or require a separately locked replay; no replay was initiated.
