# Block7/Main frozen-input origin eligibility audit — 30 October 2026

The [69-pair evidence JSON](evidence/hung-block7-input-eligibility-20261030-v1.json) (SHA-256 `0cf719bcb91adb330aabb3cf9ad5d89f32995d0c63c1a88bc254fcee83b0f4c5`) independently derives origin eligibility from the frozen Development input ZIP, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. It rehashes the entire ZIP and each budget's `schedule.jsonl`, `forecasts.jsonl` and `labels.jsonl` against its input manifest. Each of the 138 historical Block7/Main run manifests is rehashed against the pinned coverage record; its input-manifest binding must match the corresponding ZIP member.

For each entity, an origin is `created` only when the frozen schedule says so and an exact forecast-input row exists. A created origin is score eligible only when all 24 hourly labels are valid, finite and marked available no later than the next daily tick. The tool compares the resulting ordered `forecast`, `skip`, `score` and `update` lists against **both** run manifests; all 69 pairs pass.

| History budget | Pairs | Requested origins | Created forecasts | Skipped | Score eligible |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 days | 18 | 1,620 | 1,341 | 279 | 693 |
| 14 days | 24 | 2,160 | 1,293 | 867 | 735 |
| 28 days | 27 | 2,430 | 1,512 | 918 | 894 |
| **Total** | **69** | **6,210** | **4,146** | **2,064** | **2,322** |

This establishes input-derived **forecast and label eligibility** for the recorded origin schedules, including the 1,824 created origins without an eligible complete label. It does not read the original execution journals, prove each forecast value was written before the label became available, verify controller numeric traces or authorize historical-to-matched relabeling. The earlier [checkpoint payload audit](hung-block7-payload-comparison-20261029-v1.md) establishes initial state equality; the [manifest metric audit](hung-block7-manifest-metric-audit-20261030-v1.md) shows policy outcomes differ. A non-author reviewer must still decide Block7 comparability or require a separately locked replay. All 69 historical IDs remain `PENDING_PEER`.

Reproduce from repository root with the pinned ignored ZIP, coverage and 138 manifests:

```sh
python -m tools.hung_block7_input_eligibility_audit
python -m unittest tests.test_hung_block7_input_eligibility_audit -v
```

The tool checks an existing output byte-for-byte and never overwrites changed evidence.
