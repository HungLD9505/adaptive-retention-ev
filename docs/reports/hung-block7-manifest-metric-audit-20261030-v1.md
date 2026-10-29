# Block7/Main manifest metric audit — 30 October 2026

The [69-row machine-readable audit](evidence/hung-block7-manifest-metric-audit-20261030-v1.json) (SHA-256 `14ece92a6674ff8413607ee61422b3e07d878f3275eacc58582fed3f6e10daf7`) reopens the 138 SHA-pinned historical Block7 and Main manifests in the repository cache. It checks the [69 paired origin-tag schedules](hung-block7-origin-eligibility-20261028.md), matching scored-day coverage and metric-hour counts, then compares the manifest-recorded live MAE/RMSE and audit scored-day counts. It does not reopen event-journal bytes or recompute metrics from forecasts.

| Budget | Paired cells | Scored / null | Scored live records equal | Scored live records different | Audit-day counts different | Main − Block7 live MAE range, kWh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 days | 18 | 9 / 9 | 0 | 9 | 7 | −0.106480 to +0.059461 |
| 14 days | 24 | 12 / 12 | 4 | 8 | 7 | −0.038524 to +0.043079 |
| 28 days | 27 | 15 / 12 | 3 | 12 | 12 | −0.101252 to +0.180808 |
| **Total** | **69** | **36 / 33** | **7** | **29** | **26** | Mixed direction |

All 69 pairs have the same recorded scored-origin coverage, but **36/69 full metric records differ** (all 36 scored cells); 33/69 are identically null. Among the 36 scored cells, Main's live MAE is higher in 19, lower in 10 and equal in 7. A shorter controller block can produce different decisions and forecast values, so metric equality is **not** the criterion for whether the starting checkpoints and input/label eligibility are comparable. These are descriptive differences between two controller policies in Development, not a held-out gain, equivalence test or basis for selecting a policy after seeing Final outcomes.

The previously verified [checkpoint payload comparison](hung-block7-payload-comparison-20261029-v1.md) established state equality for 9 Source and 69 Target pairs. Together with equal manifest origin tags, this supports a narrower comparability argument. It still leaves event-journal byte readback, per-origin numeric/label audit and a reviewer-authored Block7 decision open. Historical runs retain their original IDs and `PENDING_PEER` status; no replay was dispatched.

Reproduce from the repository root with the ignored pinned coverage and 138 manifests:

```sh
python -m tools.hung_block7_manifest_metric_audit
python -m unittest tests.test_hung_block7_manifest_metric_audit -v
```

The tool checks existing output bytes and refuses to replace changed evidence.
