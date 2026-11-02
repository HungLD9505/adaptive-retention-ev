# Clean-tree validation of the frozen-input null-label trace

This create-only record supplements [validation v9](hung-e2e-validation-20261030-v9.md) and covers code head `e936c5b1b32049d1a980e1fccc179f1b03241819`, [report v41](hung-e2e-research-report-draft-20261030-v41.md), [gate register v64](hung-e2e-gate-register-20261030-v64.md) and the [frozen-input label audit](hung-final-null-label-input-20261030-v1.md). The locked Final input ZIP was read without modification; no frozen method, checkpoint, score source or experiment was changed.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on the clean code head with `TEMP`/`TMP` inside ignored `.cache` | **573 tests, zero failures/errors, one skip**, 127.068 s. Ignored log `.cache/hung-test-run-20261030-v15.log` SHA-256 `a65376f256f609d40d65a3894d8f40d8b9fa32a9cf652c290cd29d49be0d964e`. |
| `ruff check .` and `ruff format --check .` | Passed with locally available Ruff 0.17.3; 625 Python files format-checked in the final check. The declared pin is 0.17.0 and GitHub CI is evaluated separately. |
| Report v41 numeric audit | 90 displayed numeric cells matched tracked station-first and WAPE results; manuscript SHA-256 `d277641725edd555746b440d6400ec18f7ad201c4e259e8d40d36f4e5421e2da`. |
| Frozen-input label readback | Exact 151,254,390-byte input ZIP SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7` checked. The station-2118 9 December label record is byte-identical across all three budgets, with invalid/null hours 11:00–13:00 local. Recreated JSON matches the tracked Git blob byte-for-byte, SHA-256 `98f0b1f1c94118802a6ad2473a69545bcb26f626abe20299e6e0c35cd0d7599b`. Three synthetic regressions passed. |
| Markdown paths and manuscript wording | v41 has 120 Markdown links, gate v64 has 36 and the label audit has two; zero missing local targets. The manuscript search found no AI-generation marker string. |

The input audit proves the **proximate all-24-valid gate failure** for that one origin. It does not infer why the upstream dataset marks three hourly values invalid. Source listing, staged diff and exact-head GitHub Actions status are reported at delivery. Local tests and input hashes do not substitute for non-author scientific approval.
