# Hùng #10 draft v9 — bounded Final numeric-claim audit

This read-only CPU audit compares the published [research draft v9](hung-e2e-research-report-draft-20261029-v9.md) with the tracked [station-first Final table](hung-final-analysis-20261029-v1/station_first.csv) and [WAPE summary](hung-final-wape-20261029-v1/wape_summary.json). It does not rerun training, reconstruct forecasts, or change the frozen Final.

| Source | SHA-256 |
| --- | --- |
| Draft v9 | `b28c1485b7d1bc44dc376a390c614e80faed5a2d02281fff94884b1439fedfed` |
| Station-first table | `f01def5b1074cddf2bfda8fba98b9d7f5609dcea9510c3314ffe2645b0535c17` |
| WAPE summary | `b188d31bb5a0d433a70d224eaa0b8bf26904822defd862b1fe5cff05c2f0ee5b` |

The [auditor](../../tools/hung_report_numeric_audit_v1.py) checked **90 displayed numeric cells without mismatch**: 42 MAE panel cells (14 variants × 3 budgets), 18 ablation differences, 24 Main-versus-Target-only MAE/RMSE/gain/interval/Transfer Gain entries, and 6 Main/Target-only WAPE values. It also checked the three Main negative-transfer fractions and rejected duplicate variant/budget/reference source rows. It reads the exact table labels and fails on a missing, added, malformed or changed row. A regression changed the published Main gain and confirmed rejection.

Reproduce from the repository root:

```powershell
python -m tools.hung_report_numeric_audit_v1 --report docs/reports/hung-e2e-research-report-draft-20261029-v9.md --station-first docs/reports/hung-final-analysis-20261029-v1/station_first.csv --wape-summary docs/reports/hung-final-wape-20261029-v1/wape_summary.json
python -m unittest discover -s tests -p test_hung_report_numeric_audit_v1.py -v
```

This is a **transcription and table-consistency** check. It does not independently approve statistical uncertainty, causal method fairness, the three-station cohort scope, Block7, Hùng–Quyền parity, CHARGED lineage, Colab #39, or the GitHub review. Draft v9 remains `DRAFT / EVIDENCE-BOUND`.
