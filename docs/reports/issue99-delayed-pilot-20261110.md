# Issue #99 delayed lambda pilot (10 November 2026)

## Status

Exploratory local Calibration screen only. **Do not promote this controller to the full matrix or claim an MAE improvement.** The small-screen condition recorded before running was a lower case-mean MAE than paired Fixed with no target harm above 0.05 kWh. Neither tested setting lowered the case-mean MAE. Evaluation and Final were not used to choose these settings or score this pilot.

The worktree is `D:/Đồ Án/.cache/issue99-delayed-pilot`, branch `feat/99-delayed-pilot`, based on PR #102 commit `302fb6b00a190c788ba3ffd81268ace52a151e8a`. This is pilot code, not a replacement for PR #102 or Report 1.

## Method and binding

The existing forecast MAE plus Source-scaled latent MSE retention loss is unchanged. The pilot variant snapshots the model and Adam state immediately before a real update on arrived day V. It binds the following issued forecast W by origin and SHA-256, waits for W's complete label, then differentiates W forecast MAE through a virtual Adam update on V at the lambda actually used. A virtual/real forecast mismatch invalidates the gradient. A median of five valid gradients and four-of-five sign gate drives a bounded step, with decay toward Fixed `lambda_F=0.7984450067079901`.

Input: `D:/Đồ Án/.cache/issue99-retention-audit/.cache/issue99-input14`, manifest SHA-256 `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`. Source42: `D:/Đồ Án/.cache/issue99-retention-audit/.cache/issue99-local-gpu-source42-debug-v1/epoch-10.pt`, SHA-256 `a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b`. Source43 was extracted without overwriting from the existing source ZIP to `.cache/source43/epoch-10.pt`, SHA-256 `2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f`, matching its bundled checksum. The runner checked checkpoint/input compatibility before each run.

The pre-run case specification is `.cache/delayed-pilot-screen-spec-v1.json`: 1405/42, 2152/43, and 1693/42, first 22 daily ticks, score only matching registered Calibration origins. Each arm starts from the same Source10, target initial adaptation, lambda and fresh Adam. The Fixed arm holds lambda constant. Candidate A uses decay 0.9, meta step 10, max step 0.02, trust radius 0.25. Candidate B was tried after A had shown negligible movement: decay 0.9, meta step 200, max step 0.1, trust radius 0.4. Both use history 5 and agreement 4. B is a further exploratory Calibration probe, not a pre-registered independent result.

## Measured results

All numbers below are paired-origin mean 24-hour MAE in kWh. Delta is candidate minus Fixed; negative is favorable. The independent reader is `tools/issue99_delayed_pilot_audit.py`; machine-readable summaries are `.cache/pilot-screen-summary-v1.json` and `.cache/pilot-screen-strong-summary-v1.json`.

| Target / seed | Scored days | Fixed | A: delayed | Delta A | B: stronger | Delta B |
|---|---:|---:|---:|---:|---:|---:|
| 1405 / 42 | 20 | 5.317494 | 5.317119 | -0.000375 | 5.313754 | -0.003740 |
| 2152 / 43 | 21 | 6.539130 | 6.539466 | +0.000336 | 6.543322 | +0.004192 |
| 1693 / 42 | 21 | 2.565125 | 2.565164 | +0.000040 | 2.565883 | +0.000758 |
| Equal case mean delta | | | | **+0.00000003** | | **+0.000403** |

Candidate A made 18/20/20 delayed decisions across the three cases, with 11/4/9 gate passes. Candidate B used the same decision mechanism with larger steps. Full invocation wall seconds (including loading and warmup) for Fixed were 8.63/8.42/14.40; A took 12.40/15.53/20.85. These sequential times are descriptive, not a controlled speed benchmark. All run directories have distinct names and include their config/code binding, forecast and event commit chain, checkpoints and `run.json`:

The event audit found no `virtual_real_mismatch` skips. It found 2/1/1 no-preceding-update skips for A and the same for B, corresponding to the three listed cases. These are explicit skips, not missing scores.

| Arm | 1405 / 42 | 2152 / 43 | 1693 / 42 |
|---|---|---|---|
| Fixed | `.cache/pilot-fixed-1405-42-v1` | `.cache/pilot-fixed-2152-43-v1` | `.cache/pilot-fixed-1693-42-v1` |
| A | `.cache/pilot-delayed-1405-42-v1` | `.cache/pilot-delayed-2152-43-v1` | `.cache/pilot-delayed-1693-42-v1` |
| B | `.cache/pilot-delayed-strong-1405-42-v1` | `.cache/pilot-delayed-strong-2152-43-v1` | `.cache/pilot-delayed-strong-1693-42-v1` |

## Checks and decision

Commands used from the worktree root (the replay command was run separately for each of the nine arm/case combinations, changing `--entity-id`, source/config/output paths):

```text
python -m ev_runner.continuous_run --inputs ../issue99-retention-audit/.cache/issue99-input14 --manifest-sha256 66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9 --entity-id 1405 --source ../issue99-retention-audit/.cache/issue99-local-gpu-source42-debug-v1/epoch-10.pt --source-sha256 a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b --config .cache/pilot-delayed-seed42.json --output .cache/pilot-delayed-1405-42-v1 --device cuda --stop-after-ticks 22
python tools/issue99_delayed_pilot_audit.py --root .cache --protocol docs/reports/issue99-study-20261110/protocol-lock.json --output .cache/pilot-screen-summary-v1.json
python tools/issue99_delayed_pilot_audit.py --root .cache --protocol docs/reports/issue99-study-20261110/protocol-lock.json --candidate delayed-strong --output .cache/pilot-screen-strong-summary-v1.json
python -m unittest tests.test_issue99_delayed tests.test_issue99_continuous_runner tests.test_issue99_hypergradient -v
python -m unittest discover -s tests -q
python -m py_compile ev_control/delayed.py ev_runner/continuous.py ev_runner/continuous_run.py tests/test_issue99_delayed.py tools/issue99_delayed_pilot_audit.py
git diff --check
python -m ruff --version
```

The focused delayed-controller, legacy runner and virtual-Adam tests passed (17/17 in the implementing agent's run; a separate 9/9 focused rerun passed with `TEMP`/`TMP` inside the worktree). One initial focused test attempt failed on sandbox-protected Windows temporary paths; the in-worktree rerun passed. The README-style full `python -m unittest discover -s tests -q` ran 940 tests in 291 seconds but **failed** with one failure and 59 errors, mostly Python 3.13/Windows default cp1252 decoding or encoding of the Unicode workspace path; one fixture required Windows symlink privilege. This environment does not match the README's Python 3.12 recommendation, and the full suite is not a passing gate. `python -m py_compile` and `git diff --check` passed. Ruff was unavailable (`No module named ruff`), so lint/format checks remain open. A GRU non-contiguous-weight performance warning occurred; none of the nine real-data invocations failed.

Other README commands (`tools.sources list`, `tools.check_release`, the two experiment test suites, and `ruff format --check`) were not run in this pilot. They remain required before a PR intended for integration.

**Decision:** no full Kaggle or 4-target × 3-seed matrix for either candidate. Even the stronger variant gains only 0.00374 kWh on one case and harms the 2152/43 sentinel; this short, previously inspected Calibration slice is too small for an effectiveness claim.

Next research step: inspect whether A→V and delayed V→W gradient signs agree on Calibration and evaluate a paired counterfactual candidate/Fixed forecast guard. Register its acceptance rule and cost budget before testing. If a new bounded screen shows a practical gain without target harm, run all four targets × three seeds on Calibration; only then lock a versioned full protocol. Reserve any genuinely uninspected assessment data for final evaluation. Existing #99 and historical Final artifacts remain unchanged.
