# Clean-tree validation of bounded Final scored-origin symmetry

This create-only record supplements [validation v8](hung-e2e-validation-20261030-v8.md) and covers code head `168ec09769203bfb8956c3870c8eac0cd3d45725`, [report v40](hung-e2e-research-report-draft-20261030-v40.md), [gate register v63](hung-e2e-gate-register-20261030-v63.md) and the [coverage-symmetry audit](hung-final-coverage-symmetry-20261030-v1.md). No frozen Final input, code, lock, checkpoint or metric source was changed.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on the clean code head with `TEMP`/`TMP` inside ignored `.cache` | **570 tests, zero failures/errors, one skip**, 126.701 s. Ignored log `.cache/hung-test-run-20261030-v14.log` SHA-256 `fda8e99e16f3008a82eee26d0bf9f8f72f0d70152e89e13272e448b4b45c592e`. |
| `ruff check .` and `ruff format --check .` | Passed with locally available Ruff 0.17.3; 618 Python files format-checked. The declared pin is 0.17.0, so this remains a local-tool result, not a substitute for exact-environment CI. |
| `py -3 -m tools.sources list` | Passed as catalog listing; no raw archive download or fresh raw-byte verification is implied. |
| v40 numeric report audit | 90 displayed numeric cells matched the tracked station-first and WAPE tables; manuscript SHA-256 `a1c160eff25f23bf3643bb88f645d44fa73f001d4d952234e9c1fb6c469c7c53`. |
| Coverage-symmetry audit | Exact 360 score/run IDs, 90 issued origins per job, all 9 station/budget groups, common scored-day sets and within-group label SHA checked. All 120 unscored job-origins map to one 9 December 2022 station-2118 day repeated across 40 jobs and three budgets. Three synthetic regressions passed. Recreated JSON matches the tracked Git blob byte-for-byte, SHA-256 `6831ce58e0e679f8a91c85e4b25617db28fd72915a9cc70afc38fbf7b524e9e8`. |
| Markdown paths and manuscript wording | v40 has 119 Markdown links, gate v63 has 35 and coverage audit has two; zero missing local targets. The manuscript search found no AI-generation marker string. |

The audit's label SHA comparison is intentionally restricted to the same station and history budget. Different budget scalers can produce different serialized reconstructed floating-point labels, so this check does not assert cross-budget byte equality. Equal scored-day support within the locked comparison cells is evidence against method-specific missing-day selection; it does not prove why the upstream label is unavailable or establish real-time arrival semantics. The latest-head GitHub Actions result is read separately after pushing this documentation checkpoint.
