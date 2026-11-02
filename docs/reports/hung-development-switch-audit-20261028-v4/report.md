# Hùng Development switch-trace recovery — 28 October 2026, v4

**Scope: saved Development manifests only.** This create-only audit supersedes the narrower switch-coverage statement in [CPU audit v2](../hung-development-audit-20261028-v2/report.md); its MAE/RMSE, missing-label, uncertainty, NTR and cost results are unchanged. It does not choose a method, resolve Hùng–Qyroven implementation parity, or access Final/test inputs.

## Evidence bindings and coverage

The [851-row trace table](switch_audit_full.csv) (SHA-256 `88e0e10be97766306a790fd959e4de03f039c13cb797a7cb5a9fb0816be876b8`) contains exactly the 782 new Development job IDs plus 69 distinct historical Main anchors. Its [summary](summary.json) (SHA-256 `4f22e0da2f352909a898799ad5c1886bf227ebdf76cda2d3df57aaf037d5fbae`) contains method/budget/source counts and all source pins.

| Source | Run manifests checked | Binding used | Decision lists | No decision list |
| --- | ---: | --- | ---: | ---: |
| Kaggle new jobs | 560 | Pinned [v2 switch audit](../hung-development-audit-20261028-v2/switch_audit_kaggle.csv), whose archive/receipt/manifest SHA readback was already performed; exact job IDs and pins rechecked against the [v5 ledger](../hung-development-782-job-ledger-20261028-v5.csv). | 413 | 147 |
| Local new jobs | 222 | The 12 repository-local archives matched ledger byte lengths and full SHA-256. ZIP reading checked CRC for each selected receipt and `replay-90` manifest member. Job receipt ID/SHA and manifest SHA match both the ledger and 851-run merged source. | 208 | 14 |
| Historical Main anchors | 69 | Repository-local review capsule SHA-256 `2493e0c1f440f6b5ead7c81facb3901623c4a58252ca7fa656cf9bdb1e32953d` and its saved receipt matched. Each capsule manifest member CRC/SHA matches the capsule's internal ledger, direct repository-local copy, [69-cell pair table](../hung-block7-manifest-pairs-20261028.csv) and merged source. | 69 | 0 |
| **Total** | **851** | Distinct physical IDs; no Block7 historical alias added. | **690** | **161** |

The 69 Main manifests are preserved in the [review capsule](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/hung-review-capsule-readback-20261027.md), which had an independent provider CPU SHA/CRC readback. They do **not** have individual job receipts in that capsule. The table therefore records `CAPSULE_LEDGER_MANIFEST_NO_JOB_RECEIPT`, not the local-job receipt level. The Kaggle rows inherit their v2 proof; this recovery pass did not rehash those 560 archives. These distinctions prevent 851 manifest reads from being mistaken for 851 identical per-job proof paths.

## Observed switches

Across the 690 saved decision lists, the manifests contain **3,933 decisions and 386 observed level changes** (`selected_level != current_level`). The 161 fixed-policy rows have `issued_count` evidence but no decision list; their decision and switch fields are **null, not zero**. The exact per-run values and source levels are in the CSV.

| Method | Runs | Decision-list runs | Decisions | Observed switches |
| --- | ---: | ---: | ---: | ---: |
| `main` | 69 | 69 | 414 | 32 |
| `online_best` | 69 | 69 | 414 | 91 |
| `drift` | 69 | 69 | 414 | 114 |
| `source_error` | 69 | 69 | 414 | 54 |
| `no_source` | 69 | 69 | 414 | 53 |
| `parameter_retention` | 69 | 69 | 414 | 25 |
| `block28` | 69 | 69 | 207 | 17 |
| `fixed_retention`, `full_finetuning`, `uncertainty` | 207 | 207 | 1,242 | 0 |
| `frozen_source`, `target_only`, `seasonal_naive` | 161 | 0 | null | null |

These are saved controller-action counts, not evidence that switching improved accuracy. The methods' decision opportunities and policy definitions differ. In particular, zero observed switches for a method with a decision list is distinct from a missing list. The [CPU audit v2](../hung-development-audit-20261028-v2/report.md) remains the source for paired MAE/RMSE, uncertainty, negative transfer and cost.

## Reproduction and limits

From the repository root, use Python 3.12+ and the repository-local ignored artifacts. The command refuses to write over an existing output directory:

```powershell
python -m tools.hung_development_switch_recovery --merged .cache/development-851-merged-results.json --merged-sha256 82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d --ledger docs/reports/hung-development-782-job-ledger-20261028-v5.csv --ledger-sha256 bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004 --pairs docs/reports/hung-block7-manifest-pairs-20261028.csv --pairs-sha256 e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de --kaggle-switches docs/reports/hung-development-audit-20261028-v2/switch_audit_kaggle.csv --kaggle-sha256 2ada3cad067868000bac59378f766391a6126eb4d2b0626aa60281c7b64d112e --main-capsule .cache/review-capsule-v1/review-capsule.zip.bin --main-capsule-sha256 2493e0c1f440f6b5ead7c81facb3901623c4a58252ca7fa656cf9bdb1e32953d --output-dir docs/reports/hung-development-switch-audit-reproduction-NEW
python -m unittest tests.test_hung_development_switch_recovery -v
```

The preliminary v3 CSV/summary created before the capsule binding was added are preserved locally and are superseded by this v4. No training, provider submission, archived result overwrite, Final evaluation or test-set selection occurred.
