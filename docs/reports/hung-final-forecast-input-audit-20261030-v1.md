# Frozen Final-role forecast-input and created-schedule binding

**Scope, 30 October 2026.** This create-only, read-only audit checks actual forecast-input rows for all 373 UrbanEV/SZH Final-role IDs in Hùng's immutable Final input ZIP. It extends the [daily schedule audit](hung-final-omitted-schedule-audit-20261030-v1.md) and [370-ID input disposition](hung-final-omitted-disposition-20261030-v1.md). The [machine record](hung-final-forecast-input-audit-20261030-v1.json) has SHA-256 `e363e2cb58b5ce17753638818b1f670f683845ec9d73e0dbb2c3e7d2d361aee1`.

| Budget | Final-role `created` schedule origins | Matched forecast-input rows | Rows for 370 omitted IDs | Frozen `forecasts.jsonl` bytes / SHA-256 |
| --- | ---: | ---: | ---: | --- |
| 7 days | 25,978 | 25,978 | 25,708 | 286,070,272 / `0668ad08794d96f7b4f3c8b399f487bb8b0fd96a83ea695711db15f13fafeeb7` |
| 14 days | 26,022 | 26,022 | 25,752 | 286,596,339 / `d67ba54632b850bf183bc6f0df345f0de060a3907a11e27ef01c9b75edfcb6e8` |
| 28 days | 26,146 | 26,146 | 25,876 | 288,498,439 / `c0a22b9d3849e0ec765fa74f58fd2adb6291357446b7c86f69595a043cd9386d` |

The auditor streams and hashes each full `schedule.jsonl` and `forecasts.jsonl` member against the frozen budget manifest, decodes only Final-role forecast rows, and checks an **exact bijection** on `(entity ID, origin)` between `created` schedule entries and forecast inputs. No skipped origin has a forecast row; no created origin is missing one. Every Final-role entity's forecast count agrees with its frozen metadata. Zero duplicate forecast rows, binding errors or shape/clock failures were found.

Each forecast input has the exact declared field set, 24 hourly history labels and 24 hourly future *timestamp identities*, `X_hist[24,7]`, `C_future[24,5]`, the budget-specific run ID, its entity's scale fingerprint/value, a daily local `+08:00` origin and no future target-value payload. The audit does **not** open `labels.jsonl`, read held-out outcomes, score any method, create a Target checkpoint or authorize an extension. The 370 omitted IDs remain outside the original 360-job lock; having a valid forecast input does not establish method execution or scientifically accepted coverage.

Reproduce to a new create-only repository path:

```powershell
py -3 -m tools.hung_final_forecast_input_audit_v1 --output docs/reports/NEW_CREATE_ONLY_PATH.json
py -3 -m unittest tests.test_hung_final_forecast_input_audit_v1 -v
```

The [auditor](../../tools/hung_final_forecast_input_audit_v1.py) pins the original lock/jobset/ZIP, the schedule audit and the 370-ID disposition; it publishes counts and hashes, not the large forecast inputs.
