# Frozen Final-role omitted-ID input disposition

**Scope, 30 October 2026.** This create-only, read-only packet accounts for **every one of the 370 UrbanEV/SZH Final-role IDs** omitted from Hùng's immutable 360-job, three-station Final. Its [370-row machine record](hung-final-omitted-disposition-20261030-v1.json) has SHA-256 `e129bcc2601c8f7c4dd209dc302f3dd0d4c2c5c61a58863b5e5e28e227f4fd76`. It binds the original lock, jobset, frozen input ZIP, three input manifests, [scope gap CSV](hung-final-scope-gap-20261029-v1/scope_gap.csv), [actual prefix-row inventory](hung-final-prefix-inventory-20261030-v2.json), [Source audit](hung-final-scope-source-audit-20261030-v4.json), and four executed-code file hashes. It reads no held-out Final labels, forecasts or scores and creates no new jobset or lock.

| Input disposition over all three budgets | IDs | Meaning |
| --- | ---: | --- |
| `POSITIVE_PREFIX_ALL_BUDGETS` | 326 | Ready, positive actual pre-deployment Target training rows and scheduled forecasts at 7, 14 and 28 days. The sorted ID-set SHA matches the independent streamed prefix inventory. |
| `ZERO_PREFIX_ANY_BUDGET_READY` | 11 | Ready with a defined scale and scheduled forecasts at every budget, but at least one budget has zero Target prefix rows. Ten have zero rows throughout; ID `1004` has 0/0/11 rows at 7/14/28 days. The zero-row budgets declare `source_checkpoint_only`; positive-row budgets declare `target_initial_adaptation`. |
| `UNDEFINED_SCALE_ANY_BUDGET` | 33 | Scale is undefined in at least one budget; affected budget records declare `blocked_undefined_scale`, zero trainable rows and zero scheduled forecasts. Some IDs are ready at other budgets. |
| **Total** | **370** | Exact disjoint complement of locked IDs `2118`, `2534`, `2579` among 373 Final-role frozen IDs. No ID is silently dropped. |

For each budget, the auditor checks identity, role, initialization/count agreement, positive finite scale and scale fingerprint for `ready`, and blocked coverage semantics for `undefined_scale`. The method-code fingerprints pin `experiments/hung_sprint2/cli.py`, `single_baseline_cli.py`, `replay_inputs.py` and `dispatch_matched.py`. The implementation admits a declared `source_checkpoint_only` entity with zero actual Target updates; the Target-only CLI likewise requires zero prefix steps for that stratum. These are **code contract checks**, not proof that every method can complete a new run for these IDs. The nine generic Source checkpoint/run-manifest pairs are separately authenticated in the Source audit; no omitted-ID Target checkpoint is claimed.

This is an **intent-to-evaluate input disposition**, not an outcome-based recommendation to run only the 326 IDs. A reviewed extension must retain the 11 zero-prefix IDs as their own stratum, predeclare how the 33 scale-blocked IDs enter coverage/accounting, specify exact methods and eligibility, handle missing scored horizons, estimate resources, and freeze a new protocol without changing the original Final. Six CHARGED city scopes are absent from this ZIP and require a separate scope decision. No GPU dispatch or Final outcome comparison was performed.

Reproduce from the repository root to a new create-only path:

```powershell
py -3 -m tools.hung_final_omitted_disposition_v1 --output docs/reports/NEW_CREATE_ONLY_PATH.json
py -3 -m unittest tests.test_hung_final_omitted_disposition_v1 -v
```
