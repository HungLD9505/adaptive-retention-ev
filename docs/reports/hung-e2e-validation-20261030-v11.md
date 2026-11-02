# Clean-tree validation of the omitted-cohort Source audit

This create-only checkpoint supplements [validation v10](hung-e2e-validation-20261030-v10.md). It covers code/report head `5c8f3c6694f22d015f4b7d482ed48009a596a4e4`, the [Source audit](hung-final-scope-source-audit-20261030-v1.md), [report v42](hung-e2e-research-report-draft-20261030-v42.md) and [gate register v65](hung-e2e-gate-register-20261030-v65.md). No training, held-out label access, Final retuning or new cohort selection occurred.

| Check | Result |
| --- | --- |
| `PYTHONUTF8=1; py -3 -m unittest discover -s tests -q` on clean `5c8f3c6`, with `TEMP`/`TMP` inside ignored `.cache` | **576 tests, zero failures/errors, one skip**, 127.652 s. Ignored log `.cache/hung-test-run-20261030-v16.log` SHA-256 `7a61c1c3a01233b24ec36b8aaed93e148a662f061c5c0bbe229d8ddb23257be2`. |
| `ruff check .` / `ruff format --check .` | Passed with locally available Ruff 0.17.3; 630 Python files format-checked. The declared pin is 0.17.0. |
| Focused Source audit regressions | Three passed: real nine-Source/370-ID inventory, changed Source fingerprint rejection, changed jobset fingerprint rejection. |
| `tools.hung_report_numeric_audit_v1` on report v42 | 90 numeric cells matched tracked Final station-first/WAPE tables; report SHA-256 `8b24a23b4375bd7679494b8c6c5d3f518cdd592fc0e24abfd01d7e314c4ca8e9`. |
| Source audit output | Nine checkpoint files loaded with `weights_only=True`; 360 jobset Source/input bindings reconciled; 326/370 omitted IDs pass the all-budget minimal-input filter. Machine JSON SHA-256 `4570150203d98628147ad66182838bafbab3ff211833e8b0ffe7838290041e4c`. |
| Markdown paths and wording | Report v42 has 122 links, gate v65 37 and Source audit report five; zero missing local targets and no AI-generation marker string. |
| `python -m tools.sources list`, staged diff | Source catalog listed; `git diff --cached --check` passed before code/report commit. |

The full test log contains expected negative-fixture messages (e.g. checksum and undefined-scale cases) and ends `OK (skipped=1)`. Software and checkpoint checks do not substitute for method-specific Target preflight, broader cohort authorization, non-author scientific review or GitHub CI. Exact-head CI status is reported on PR #72 after this checkpoint.
