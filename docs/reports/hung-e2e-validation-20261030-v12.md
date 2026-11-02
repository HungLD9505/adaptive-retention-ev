# Clean-tree validation of Source lineage and Development head embedding

This create-only checkpoint supplements [validation v11](hung-e2e-validation-20261030-v11.md) and covers clean code/report head `3db7bc74106211f572fdb57b1b584c7d17660e3c`: [Source/Target-metadata audit](hung-final-scope-source-audit-20261030-v2.md), [trained head embedding](hung-q-head-embedding-audit-20261030-v1.md), [report v43](hung-e2e-research-report-draft-20261030-v43.md) and [gate register v66](hung-e2e-gate-register-20261030-v66.md). Neither frozen Final nor earlier run artifacts were changed.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on clean `3db7bc7`, with `TEMP`/`TMP` inside ignored `.cache` | **582 tests, zero failures/errors, one skip**, 128.249 s. Ignored log `.cache/hung-test-run-20261030-v17.log` SHA-256 `d3a57ff9c04b20e74f65b3535ea9c11ef2062c49000427ef0b964e16f6c17c86`. |
| `ruff check .` / `ruff format --check .` | Passed with locally available Ruff 0.17.3; 639 Python files format-checked. The declared pin is 0.17.0. |
| Focused audit regressions | Nine passed across Source audit v1/v2 and head embedding; changed Source/jobset/manifest fingerprints and unreviewed head width are rejected. |
| Source audit v2 reproduction | Frozen lock/ZIP/jobset, nine Source checkpoint/run-manifest bindings and 370 omitted-ID metadata checked. Recreated machine JSON is byte-identical to [v4](hung-final-scope-source-audit-20261030-v4.json), SHA-256 `11b443ea1f0ad2f3b8394d75590aba4c55a7c1138256230707f941c4c6e0e0d6`. |
| Head embedding reproduction | One real trained Development Target checkpoint and 14 forecast origins; label member opened only after initial forecast comparison. Recreated machine JSON is byte-identical to [v4](evidence/hung-q-head-embedding-audit-20261030-v4.json), SHA-256 `a6efceb25a48a3bd2045d64e1ff34285d974c145a306361d4abf7a0bd36068be`. |
| Report v43 numeric/links | 90 displayed Final numeric cells matched source tables; manuscript SHA-256 `15781cbfe2c815d3b96883270109013abeee2858ddbca0ee66c09a1a4aec0877`. Local link check found zero missing targets in report v43 (124 links), gate v66 (38), Source audit v2 (five) and head-embedding report (six). No AI-generation marker string was found. |
| Staged diff | `git diff --cached --check` passed before the code/report commit. |

The full log includes expected negative-fixture messages and ends `OK (skipped=1)`. The head embedding is an initial-function comparison plus one fresh-optimizer diagnostic; it does not prove trained runner/controller parity. Source/Target metadata do not authorize a broader Final cohort. GitHub CI and non-author scientific review remain separate gates; exact-head CI status is reported on PR #72 after this checkpoint.
