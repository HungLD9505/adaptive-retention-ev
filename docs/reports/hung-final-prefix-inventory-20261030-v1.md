# Frozen Final-role prefix training inventory for omitted UrbanEV IDs

**Scope, 30 October 2026.** This read-only audit extends the [Source/Target metadata audit](hung-final-scope-source-audit-20261030-v2.md) by checking actual **pre-deployment training rows** in the same locked `inputs.zip`, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. It does not inspect post-deployment Final outcomes, compute a forecast metric, fit a model, select stations or authorize an extension. The [machine output](hung-final-prefix-inventory-20261030-v2.json) has SHA-256 `e2474fb22a16e2d877a7ed43db760e1b96dbf0c9ad29446c08d34ce2dcc01cf2`.

| Budget | Frozen `training.jsonl` member bytes | SHA-256 | Final-role prefix rows, all 373 IDs | IDs with rows | Omitted IDs passing input inventory |
| --- | ---: | --- | ---: | ---: | ---: |
| 7 days | 453,615,715 | `ce230356f23fe05c7a68f5e8a35e3c1284375f02f537dece89558ad107ef388c` | 1,974 | 329 | 326 |
| 14 days | 481,502,337 | `eadb4bb38d0e3dce1eded428ba4d806346cefc4e09840fa65814670edfd0999c` | 4,275 | 329 | 326 |
| 28 days | 535,897,754 | `a58d76127ff3decf9d3f187d2666d98aeb76d4eee75163b9de9f9520e22a6ece` | 8,746 | 333 | 330 |

The auditor checks each member's complete bytes and SHA against the budget manifest, then requires every Final-role entity's actual row count to equal its frozen `initial_trainable` metadata. Every counted row has the expected UrbanEV/SZH entity, scale ID, 24-hour history/calendar and target shapes, finite nonnegative **prefix** target values, distinct origin, hourly label timeline and target end strictly before `2022-12-01T00:00:00+08:00` deployment. It records **zero** count mismatch, invalid prefix or late row across the three members. It publishes only counts and hashes, not energy observations. The intersection of omitted IDs with qualifying rows at all three budgets is exactly **326**, with sorted-ID-set SHA-256 `c170ec8aeb0a9dea8f6a2431e3dcc695959af8e949c4f5a13092f7d7eff4f972`.

This establishes that the 326 have real, causally eligible prefix training rows under the frozen input contract, in addition to available generic Source checkpoints and Target initialization metadata. It does **not** prove successful Target training/replay, method-specific behavior, usable post-deployment scores, budget fairness, capacity or scientific approval. The 44 other omitted IDs fail the all-budget input filter; six CHARGED city scopes remain outside this ZIP. No extra jobset or lock is created.

Reproduce from the repository root to a new output path:

```powershell
py -3 -m tools.hung_final_prefix_inventory_v1 --output docs/reports/NEW_CREATE_ONLY_PATH.json
py -3 -m unittest tests.test_hung_final_prefix_inventory_v1 -v
```

The [auditor](../../tools/hung_final_prefix_inventory_v1.py) pins the frozen lock, jobset, input ZIP, scope-gap CSV and Source audit. Four focused tests cover the real inventory, a valid row, late-label rejection and malformed-target rejection. The full uncompressed training members are streamed; no raw archive, checkpoint or prior output is modified.
