# Clean-tree validation of frozen Final prefix inventory

This create-only checkpoint supplements [validation v12](hung-e2e-validation-20261030-v12.md) and covers clean code/report commit `ed51b8d31fb77f1061d8f7bae1d1be12293259e8`: the [prefix inventory](hung-final-prefix-inventory-20261030-v1.md), [report v44](hung-e2e-research-report-draft-20261030-v44.md), and [gate register v67](hung-e2e-gate-register-20261030-v67.md). Frozen inputs, the 360-job lock, saved run outputs and earlier reports were not modified.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on clean `ed51b8d`, with `TEMP`/`TMP` inside ignored `.cache` | **586 tests, zero failures/errors, one skip**, 139.702 s. Ignored log `.cache/hung-test-run-20261030-v18.log` SHA-256 `03acdfc05b7c40517cf1214b6cba3a43a1b76cd368f1f28f4e940170380987ed`. |
| `ruff check .` / `ruff format --check .` | Passed with locally available Ruff 0.17.3; 645 Python files format-checked. The declared pin is 0.17.0. |
| Focused prefix inventory tests | Four passed: pinned real frozen inventory, valid row, late-label rejection, and malformed-target rejection. |
| Frozen prefix reproduction | All three training members were streamed and matched manifest bytes/SHA. The machine output is [v2](hung-final-prefix-inventory-20261030-v2.json), SHA-256 `e2474fb22a16e2d877a7ed43db760e1b96dbf0c9ad29446c08d34ce2dcc01cf2`. Counts: 1,974/4,275/8,746 Final-role prefix rows at 7/14/28 days; 326 omitted IDs meet the all-budget input inventory. |
| Report v44 numeric/links | 90 displayed Final numeric cells matched source tables; manuscript SHA-256 `771e6ecbdd4778cbbdb3b2f6fdf07538472d5149cb0599e240d54f37028e8744`. Local link check found zero missing targets in the three new Markdown files and no AI-generation marker string. |
| Staged diff | `git diff --cached --check` passed before the code/report commit. |

The test log contains expected negative-fixture diagnostics and ends `OK (skipped=1)`. The inventory validates pre-deployment input rows, not method-specific training, post-deployment scores, a broadened Final lock, or non-author approval. CI and peer review are separate gates.
