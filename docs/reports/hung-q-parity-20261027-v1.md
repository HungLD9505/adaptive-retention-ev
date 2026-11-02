# Bounded Hung–Qyroven implementation parity audit — 2026-10-27

**Scope:** synthetic component and runner fixtures for #39/#19–#21. This audit did not open Final labels, train a Development job, reuse historical scores as matched scores, or approve either implementation. Report 1 §§5–6 and `docs/SPRINT_PLAN.md` are the method requirements. [Machine-readable evidence](evidence/hung-q-parity-20261027-v1.json) records exact file hashes and outputs.

## Source identity and methods

Qyroven was extracted from commit `83b877e16e7e690d93bb1f7736ce1870ef08fadd`; Hung's historical comparison code from `e85a53cd02deaa3a3440df8c6922eb679773801b`; the current Hung branch is `c1c83a0e342536ea660b7b48eb66882f4459b959`. Both frozen checkouts are ignored, create-only local extractions. Qyroven's existing `tools.compare_hung_components` was rerun against byte-pinned Hung components. A new create-only 14-day script reran the varying-score decision with the same scores, levels, Bmin, alpha, segment, resamples and seed for both controllers. A tiny CUDA fixture loaded identical GRU encoder weights, applied the same synthetic input, and compared latent-retention loss and gradients. No full training step was run.

The Qyroven controller file at the cited `83b877e` commit has SHA-256 **`27b8d7709fc07442cc4461082e4d6599108ed70591f4398c5c5cc062980c7174`**, confirmed by both `git show` bytes and the extracted file. The earlier `hung-39-controller-variance-20261026.md` states **`27b8d7709fc07442cc4461082e4d6599108ed70591f4398c5c60a3d60e6f36a`** for that file. Its decision numbers reproduce exactly, but its file hash does not match that Git revision. Preserve that historical report and use the newly measured hash for this audit; the mismatch requires reviewer correction of the provenance record, not a silent edit to old evidence.

## Observed component results

| Check | Result | Scope limit |
| --- | --- | --- |
| Shared GRU encoder weights and synthetic `[2,24,7]` history | CPU and local CUDA maximum latent difference **0** | Does not compare complete forecasts. |
| Latent retention loss with `epsilon=0.001` and frozen source | CPU both `2.5089153428333866`; CUDA both `2.508915342833387`. Target gradients exactly equal; source gradients absent. | Synthetic tensor, not real target adaptation. |
| Full head | Qyroven 52,376 vs Hung 41,696 total parameters. The head topologies differ, so forecast/checkpoint equality is **not established**. | Must agree one architecture before a matched prediction/gradient comparison. |
| CUDA component fixture, seed 123 | RTX 3050 Ti, PyTorch `2.8.0+cu126`; historical run peak allocated 752,640 bytes, reserved 2,097,152 bytes, elapsed 0.784 s. Current Hung latent path also matched, elapsed 0.296 s at the same peak. | Tiny fixture costs are **not** shard throughput/VRAM estimates. |

The current Hung `model.py` has the same SHA as historical. Its `retention.py` adds Parameter Retention support; the default latent path passed the CUDA fixture. Its controller decision payload adds fields for other policies, but the tested confidence decision remained as below. This does not equate the new variants with Qyroven's implementation.

## Varying-day decision discrepancy

With 14 complete paired days, levels `(0,0.1,0.2)`, active `0`, Bmin `5`, delta `0`, Bonferroni alpha `0.05`, noncircular segment `2`, `100` resamples and seed `7`, daily losses were `(2.0, 1.8+0.3*((i%5)-2), 1.75+0.3*((i%7)-3))` for `i=0..13`.

| Controller | LCB for 0.1 | LCB for 0.2 | Decision |
| --- | ---: | ---: | --- |
| Qyroven `83b877e` | −0.025535714285714307 | −0.061249999999999964 | Keep 0 |
| Hung `e85a53c` and current `c1c83a0` | +0.007142857142857102 | −0.07142857142857138 | Switch to 0.1 |

This independently reproduces the earlier diagnostic. That report isolates bootstrap stream derivation as sufficient to reverse **this** marginal fixture; quantile interpolation also differs. Report 1 permits a one-sided day-block-bootstrap LCB but does not prescribe these conventions. The co-leads/reviewer must select and lock a convention on methodological and Development-only grounds; choosing the one with a better observed model score would be invalid. Historical runs keep their original identity.

## Runner invariants checked, direct trace still open

Qyroven's 12 `test_prequential_runner.py` cases passed, including forecast durability before label access, delayed/missing labels, block keep, audit isolation, exact daily model/optimizer/RNG resume, and tamper rejection. Historical Hung's 6 `test_hung_runner.py`, 4 `test_hung_resume.py` and 7 `test_hung_replay_inputs.py` cases passed, including forecast-before-label, forced switch, missing/late labels, block boundary, isolated audit, split replay and resume. The current Hung branch separately passed runner 6/6 and resume 4/4. Qyroven's 11 `test_issue19_model.py` cases also passed. These are **independent test suites** with different model/config and timeline fixtures. They establish each implementation's tested invariants but **do not establish one matched event-by-event trace or identical state**. Hung's historical Source/Target checkpoints without RNG snapshots retain their earlier resume limitation; passing new runner fixtures does not retrofit those files.

Before #39 integration, use one agreed input hash/entity/budget/scaler, identical seed and update order, common model/head and Source/Target state to compare predictions, latent vectors, forecast+retention loss, gradients, controller inputs/decisions, missing/boundary events and checkpoint resume at a declared tolerance. Resolve the head, bootstrap and one-pass Source/training-configuration differences, then obtain independent review. No #39 acceptance or shared-module merge is claimed here.

## Commands, files and limits

Ran `git archive` for the two pinned commits, Qyroven's `python -m tools.compare_hung_components`, the new `parity-varying-day-20261027-v1.py` on historical/current Hung, and `parity-gpu-20261027-v1.py` on historical/current Hung. Focused unittest runs: Qyroven runner **12/12**, model **11/11**; historical Hung runner **6/6**, resume **4/4**, replay-input **7/7**; current Hung runner **6/6**, resume **4/4**; all exit 0. Evidence JSON parsed successfully and `git diff --check` passed. Python/PyTorch environment was local Python 3.13 / PyTorch 2.8 CUDA 12.6, not the historical Qyroven PyTorch 2.11 Colab environment. No full suite or real-data archive was rerun. Repository files added: this report and the JSON evidence. Ignored `.cache` holds the two frozen source extractions, scripts and raw outputs. The first `git worktree add` attempt was denied write access to `.git/worktrees`; create-only `git archive` extraction succeeded. The initial varying-day evidence script referenced a nonexistent Qyroven `lower_bounds` field; corrected to its `comparisons` field before producing the successful output. A PDF console extraction initially hit Windows CP1252 encoding and succeeded with UTF-8; Report 1 text was read. `python -m ruff` was unavailable in this Python environment, so Ruff lint/format remain unrun for the ignored scripts; the two tracked deliverables are Markdown and JSON only. No focused test failure remains.
