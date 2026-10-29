# Clean-tree validation of Final gain aggregation audit

This record supplements [validation v7](hung-e2e-validation-20261030-v7.md) and covers code head `b9e0e2712068c1fff4202b30663a7c70d6b04f72` plus [research draft v39](hung-e2e-research-report-draft-20261030-v39.md), [gain audit v1](hung-final-gain-aggregation-audit-20261030-v1.md) and [gate register v62](hung-e2e-gate-register-20261030-v62.md). No frozen experiment, input, lock, training output or previously reported metric changed.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on the clean code head, with `TEMP`/`TMP` inside ignored `.cache` | **567 tests, zero failures/errors, one skip**, 126.666 s. Ignored log `.cache/hung-test-run-20261030-v13.log` SHA-256 `1125b4db71097461326d573b7e88a58675d6a40462bf6b7f10180ee9263f56be`. |
| `ruff check .` and `ruff format --check .` | Passed; 612 Python files format-checked with locally available Ruff 0.17.3. The dependency declaration pins 0.17.0; this local version difference and the absence of CI execution are explicit. |
| `py -3 -m tools.sources list` | Passed; catalog listing only, not a fresh raw-archive download or checksum verification. |
| Report numeric audit on v39 | 90 displayed numeric cells checked against the tracked station-first and WAPE tables; report SHA-256 `c117f489785f7c4d0cffb2d533419f26ac590312ed52ec716862d74ad1c81e63`. |
| Gain reaggregation | All nine Main/Target-only physical pairs at each budget matched the published station-first MAE, gain, Transfer Gain and NTR. Four synthetic tests cover the unequal estimands, missing seed, published-ratio mismatch, stable LF serialization and create-only refusal. The regenerated JSON is byte-identical to the tracked Git blob, SHA-256 `ce1c1e883c01c42526129b89a9650a4b7604ce10448b663ae94495122d91583c`. |
| Markdown paths and wording | v39 has 118 local/remote Markdown links with zero missing local targets; gate v62 has 34 and gain audit v1 has 3, also zero missing local targets. No AI-generation marker string was found in the manuscript. |

**Failed first attempt and cause.** A full-suite run on the dirty working tree reported 565 tests, two proxy-calibration fixture errors and one skip. Those fixtures intentionally require their generated run manifest to bind a clean Git commit; untracked report/code files made the generated `worktree_status` nonempty, so `select` rejected it with `Calibration run identity/config mismatch`. After committing the new evidence, both affected CPU/CUDA fixtures passed separately, followed by the clean-tree 567-test pass above. The failed log remains in ignored `.cache/hung-test-run-20261030-v11.log`; no expected hash or fixture was weakened to conceal it.

The first local Ruff invocation through `py -3 -m ruff` failed because that interpreter has no Ruff module. The repository-local Kaggle CLI environment provided Ruff 0.17.3; its final full-repository lint/format checks passed. The final staged diff and exact-head GitHub Actions status are checked at delivery. Software validation does not supply independent scientific review, authenticated provider version bindings or full-cohort generalization.
