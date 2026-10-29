# Clean-tree validation of Final schedule and Development controller sensitivity

This create-only checkpoint supplements [validation v14](hung-e2e-validation-20261030-v14.md) and covers clean code/report commit `2f640e1674500331e52acf7a222e1a39ef95cd44`: the [frozen Final-role schedule audit](hung-final-omitted-schedule-audit-20261030-v1.md), [Development controller-rule sensitivity](hung-q-controller-decision-sensitivity-20261030-v1.md), [report v46](hung-e2e-research-report-draft-20261030-v46.md), and [gate register v69](hung-e2e-gate-register-20261030-v69.md). Neither frozen Final nor historical Development outputs were changed.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on clean `2f640e1`, with `TEMP`/`TMP` inside ignored `.cache` | **599 tests, zero failures/errors, one skip**, 143.494 s. Ignored log `.cache/hung-test-run-20261030-v20.log` SHA-256 `56a5195d99b0cd9f5908ce4886843771dd2540a0d25aac27787f6b3f60339bc3`. |
| `ruff check .` / `ruff format --check .` | Passed with locally available Ruff 0.17.3; 660 Python files format-checked. Declared pin is 0.17.0. |
| Focused regressions | Nine passed: five schedule-coverage tests and four controller-sensitivity tests. |
| Schedule reproduction | Recreated JSON byte-identically, SHA-256 `b4211712fc9c25d4343b076c29d1489a8d7d45db54a91011c9fe310daf9bed4e`; 373 Final-role ID schedules at every budget, 90 origins each, zero missing/duplicate entity schedules. |
| Controller sensitivity reproduction | Recreated JSON byte-identically, SHA-256 `04f28827cc1782e61e2c4a36a8df38293fc5ba88fe4378d93fe9a41873f883e4`; 414/414 saved Development Main decisions replayed, three fixed-draw quantile changes and eight full-Q-rule changes among 168 bootstrap-eligible boundaries. |
| Report v46 numeric/links | 90 displayed Final numeric cells matched source tables; manuscript SHA-256 `384337c3797155813f89e147256d48bbc591145622c137f139d713cb18950db9`. All four new Markdown files had zero missing local links or AI-generation marker strings. |
| Source listing and staged diff | `rg --files` listed 877 repository-visible paths. `git diff --cached --check` passed before commit; newly added files contain no credential, checkpoint or raw archive. |

The full test log contains expected negative-fixture diagnostics and ends `OK (skipped=1)`. The controller comparison is conditional on Hùng's already saved Development score histories at each original boundary; it is not a Qyroven model/policy replay or an acceptance of a canonical contract. Exact-head GitHub CI and non-author review remain separate gates.
