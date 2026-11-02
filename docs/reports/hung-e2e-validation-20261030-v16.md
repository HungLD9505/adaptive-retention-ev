# Clean-tree validation of frozen Final forecast-input binding

This create-only checkpoint supplements [validation v15](hung-e2e-validation-20261030-v15.md) and covers clean code/report commit `786390d3c49fbb9246ec1b66327540e81bdda349`: the [forecast-input audit](hung-final-forecast-input-audit-20261030-v1.md), [report v47](hung-e2e-research-report-draft-20261030-v47.md), and [gate register v70](hung-e2e-gate-register-20261030-v70.md). The original Final lock, input ZIP, saved outputs and earlier checkpoints were not modified.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on clean `786390d`, with `TEMP`/`TMP` inside ignored `.cache` | **604 tests, zero failures/errors, one skip**, 159.080 s. Ignored log `.cache/hung-test-run-20261030-v21.log` SHA-256 `ff43ba326dd15b310024463a32f706406e9dc463cddf3af5671d2926374efbc6`. |
| `ruff check .` / `ruff format --check .` | Passed with locally available Ruff 0.17.3; 666 Python files format-checked. Declared pin is 0.17.0. |
| Focused forecast-input regressions | Five passed: real pinned bijection, valid row, scale mismatch, hourly clock mismatch and rejection of a future target-value payload. |
| Frozen input reproduction | Recreated [machine JSON](hung-final-forecast-input-audit-20261030-v1.json) byte-identically, SHA-256 `e363e2cb58b5ce17753638818b1f670f683845ec9d73e0dbb2c3e7d2d361aee1`. Manifest-pinned `forecasts.jsonl` members match all 25,978/26,022/26,146 created Final-role origins, with zero missing, extra or duplicate rows. |
| Report v47 numeric/links | 90 displayed Final numeric cells matched source tables; manuscript SHA-256 `efc0b62cc7fb7f8648e96224f7af2e94251cbfe2be6e38efc812b1a65dd9ea63`. Three new Markdown files had zero missing local links or AI-generation marker strings. |
| Source listing and staged diff | `rg --files` listed 884 repository-visible paths. `git diff --cached --check` passed before commit; newly added files contain no credential, checkpoint or raw archive. |

The full test log contains expected negative-fixture diagnostics and ends `OK (skipped=1)`. This is frozen input presence and shape evidence, not held-out label eligibility, method-specific training, additional Final evaluation or independent scientific approval. Exact-head GitHub CI remains a separate gate.
