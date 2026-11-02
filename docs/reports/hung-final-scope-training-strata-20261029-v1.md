# Hùng Final omitted-cohort target-prefix strata — 29 October 2026

**Scope:** read-only follow-up to the [370-ID frozen-input gap ledger](hung-final-scope-gap-20261029-v1/README.md). It reopens the **same** locked input ZIP and jobset through `tools.hung_final_scope_gap.read_frozen_inputs` and `scope_gap`; that reader rehashes the 360-job lock, jobset, input ZIP, each budget's manifest and `entities.jsonl`. No Final label values, saved forecasts, MAE/RMSE or provider run were read. This is a prospective input-stratum inventory, not an authorized new Final plan.

The frozen lock SHA-256 is `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`; the input ZIP SHA-256 is `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. The [gap CSV](hung-final-scope-gap-20261029-v1/scope_gap.csv) SHA-256 is `c4c7a067bb45c048c4ec2da58b321d72033e23e3a4467e5378069a6ce68bd681`. The three locked IDs remain `2118`, `2534`, `2579`; the other 370 Final-role IDs are unchanged.

| Omitted UrbanEV/SZH status | 7 days | 14 days | 28 days |
| --- | ---: | ---: | ---: |
| `ready` in frozen inventory | 337 | 338 | 342 |
| `ready` and `initial_trainable > 0` | 326 | 326 | 330 |
| `ready` and `initial_trainable = 0` | 11 | 12 | 12 |
| `ready` and `scheduled_forecasts > 0` | 337 | 338 | 342 |

Across all three budgets, **337** omitted IDs are `ready`; **326** of these have a positive initial trainable count in all three budgets and scheduled forecasts in all three. Of the other **11** all-budget-ready IDs, ten have zero initial trainable examples at every budget and one (`1004`) has zero at 7/14 days and 11 at 28 days. Their exact IDs are `1004`, `1023`, `1075`, `1079`, `1106`, `1274`, `1737`, `1851`, `2193`, `2314`, `2609`. All 11 still have positive scheduled-forecast counts in every budget. The existing [scope gap report](hung-final-scope-gap-20261029-v1/README.md) separately records 33 IDs with `undefined_scale` in at least one budget; these are not in the 337 all-ready group.

Zero initial examples are **not** equivalent to a failed job or a zero error. The executed code's `source_checkpoint_only` target-initialization stratum is designed for no target-prefix examples, and [`target-only-init`](../../experiments/hung_sprint2/single_baseline_cli.py) permits an exact zero-step prefix pass when the frozen entity inventory declares that stratum. This code inspection does not prove that all methods, labels and checkpoints would pass a new 370-ID execution preflight. In particular, `ready` does not certify complete held-out label horizons, and Final labels must not be inspected to select the expansion cohort.

## Reproduction and decision boundary

From the repository root, use the pinned reader and derive the counts without opening label members:

```powershell
@'
from tools.hung_final_scope_gap import LOCK, JOBSET, INPUTS, BUDGETS, read_frozen_inputs, scope_gap
jobset, entities, _ = read_frozen_inputs(LOCK, JOBSET, INPUTS)
rows, _ = scope_gap(jobset, entities)
for budget in BUDGETS:
    ready = [row for row in rows if row[f"status_{budget}d"] == "ready"]
    print(budget, len(ready), sum(row[f"initial_trainable_{budget}d"] > 0 for row in ready),
          sum(row[f"initial_trainable_{budget}d"] == 0 for row in ready),
          sum(row[f"scheduled_forecasts_{budget}d"] > 0 for row in ready))
all_ready = [row for row in rows if all(row[f"status_{b}d"] == "ready" for b in BUDGETS)]
positive_all = [row for row in all_ready if all(row[f"initial_trainable_{b}d"] > 0 for b in BUDGETS)]
print("all_ready", len(all_ready), "positive_all", len(positive_all))
'@ | python -X utf8 -
```

The read-only command exited 0 with rows `(7,337,326,11,337)`, `(14,338,326,12,338)`, `(28,342,330,12,342)`, then `all_ready 337 positive_all 326`. A reviewer must decide the original cohort/city scope and predeclare handling of zero-prefix and undefined-scale strata before any new experiment identity or compute allocation. The bounded 360-job Final lock and every historical output remain immutable.
