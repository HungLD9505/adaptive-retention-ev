# Clean-tree validation of the complete omitted-ID input disposition

This create-only checkpoint supplements [validation v13](hung-e2e-validation-20261030-v13.md) and covers clean code/report commit `0b3dd31fc251186971854c5fc7ff427112b32d8f`: the [370-ID disposition](hung-final-omitted-disposition-20261030-v1.md), [report v45](hung-e2e-research-report-draft-20261030-v45.md), and [gate register v68](hung-e2e-gate-register-20261030-v68.md). Frozen input and 360-job Final outputs were not modified.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on clean `0b3dd31`, with `TEMP`/`TMP` inside ignored `.cache` | **590 tests, zero failures/errors, one skip**, 139.155 s. Ignored log `.cache/hung-test-run-20261030-v19.log` SHA-256 `d59b9f7d7ac71757fea21d58339ba85947c1931661e26e60cbfac8b73ec73a92`. |
| `ruff check .` / `ruff format --check .` | Passed with locally available Ruff 0.17.3; 651 Python files format-checked. Declared pin is 0.17.0. |
| Focused disposition tests | Four passed: real 370-ID partition, mixed 0/0/11 prefix mode, blocked undefined-scale coverage and rejected mode/count mismatch. |
| Disposition reproduction | Auditor output was reproduced byte-identically at a create-only ignored path. [Machine JSON](hung-final-omitted-disposition-20261030-v1.json) SHA-256 `e129bcc2601c8f7c4dd209dc302f3dd0d4c2c5c61a58863b5e5e28e227f4fd76`; counts 326 positive-prefix-all-budget, 11 zero-prefix-any-budget-ready and 33 undefined-scale-any-budget. |
| Report v45 numeric/links | 90 displayed Final numeric cells matched source tables; manuscript SHA-256 `911978bc2a85152a7c900f61042218a0ad6c3b458e9dc8dae0acbf9130558026`. New Markdown files had zero missing local links or AI-generation marker strings. |
| Source listing and staged diff | `rg --files` listed 866 repository-visible paths. `git diff --cached --check` passed before commit; newly added files contain no credential, checkpoint or raw archive. |

The test log contains expected negative-fixture diagnostics and ends `OK (skipped=1)`. This input disposition is neither a method-specific execution proof nor a reviewed extension lock. Exact-head GitHub CI and non-author scientific approval remain separate gates.
