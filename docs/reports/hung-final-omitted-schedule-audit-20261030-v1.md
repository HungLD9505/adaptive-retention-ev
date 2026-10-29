# Frozen Final-role daily schedule coverage for the omitted cohort

**Scope, 30 October 2026.** This read-only audit joins the [complete 370-ID input disposition](hung-final-omitted-disposition-20261030-v1.md) to all three `schedule.jsonl` members in the same immutable Final input ZIP. The [machine output](hung-final-omitted-schedule-audit-20261030-v1.json) has SHA-256 `b4211712fc9c25d4343b076c29d1489a8d7d45db54a91011c9fe310daf9bed4e`. It reads no held-out labels, forecasts, checkpoints or result metrics and creates no extension lock.

Each member was checked against the pinned manifest bytes/SHA. For **every one of 373 Final-role IDs** at each 7/14/28-day budget, the auditor requires exactly the 90 daily origin timestamps from `2022-12-01` through `2023-02-28` local time, one status per origin, and exact agreement with the frozen entity's requested/created/history-skip/undefined-scale counts. There are **zero missing, duplicate or mismatched entity schedules**. The original three locked IDs are included in this schedule integrity check; the disposition summaries below concern the 370 omitted IDs.

| Budget | All 373: created | All 373: history skipped | All 373: scale blocked | Omitted 326 positive-prefix: created / history skipped | Omitted 11 zero-prefix-any-budget: created / history skipped | Omitted 33 undefined-scale-any-budget: created / history skipped / scale blocked |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 days | 25,978 | 4,622 | 2,970 | 24,899 / 4,441 | 809 / 181 | 0 / 0 / 2,970 |
| 14 days | 26,022 | 4,668 | 2,880 | 24,899 / 4,441 | 809 / 181 | 44 / 46 / 2,880 |
| 28 days | 26,146 | 4,904 | 2,520 | 24,899 / 4,441 | 809 / 181 | 168 / 282 / 2,520 |

Every all-373 row sums to **33,570 requested origins** (373 × 90). The 33-ID cross-budget stratum is fully scale-blocked at seven days, but some of those IDs become ready at 14 or 28 days; their created and history-skipped origins remain visible. The 11 zero-prefix-any-budget IDs also have forecast inputs: zero **initial training** examples does not mean zero forecast opportunities. These are input schedule and coverage facts, not scorable-label counts or completed method jobs. A reviewed extension must predeclare how blocked origins and zero-prefix strata enter method, coverage and paired-score denominators; no blocked origin is imputed as a zero-error forecast.

Reproduce create-only from the repository root:

```powershell
py -3 -m tools.hung_final_omitted_schedule_audit_v1 --output docs/reports/NEW_CREATE_ONLY_PATH.json
py -3 -m unittest tests.test_hung_final_omitted_schedule_audit_v1 -v
```

The [auditor](../../tools/hung_final_omitted_schedule_audit_v1.py) pins the original lock, jobset, input ZIP and 370-ID disposition. It validates daily origin sets and status counts without opening `labels.jsonl`; successful input scheduling does not establish usable scores, trained Target checkpoints, method-specific execution or a scientifically approved wider Final.
