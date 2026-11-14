# Issue #99: joint retention and Fixed-lambda local probe (10 November 2026)

## Decision

**Recommended pair for the current #99 study:** keep Report 1's Source-scaled latent MSE retention and the previously selected Fixed `lambda = 0.5634538227695682`. This is the pair with the stronger existing protocol evidence. A small joint local search found a numerically lower Calibration macro MAE at pseudo-Huber `delta=2`, `lambda=2`, but the gain was below the pre-existing `0.05` kWh practical threshold, target 1693 worsened by more than `0.05` kWh, and the seed-44 check reversed the apparent gain. It is not a justified replacement or a new scored result.

The numerical winner **among the tested pairs on reused Calibration** is different from the recommended pair; both facts are reported below. No Evaluation or Final score was used to select the formula or lambda. Since this Calibration window had already been inspected in #99, none of these comparisons is an independent test.

## Formulas and paired setup

All arms retain forecast MAE, 14-day input, matching Source10 seed checkpoint, fresh target clone and Adam, three initial target epochs, one online epoch per arrived complete label, and the first 22 replay ticks. Each arm scores the same 19 registered Calibration origins per target. The Fixed coefficient is constant for both initial adaptation and online updates.

Let `u = (z_target - stopgrad(z_source)) / (stopgrad(source_scale) + epsilon)`:

| Loss arm | Penalty |
| --- | --- |
| `mse` | `R = mean(u²)` (repository/Report 1) |
| `pseudo_huber_2` | `R = mean[8(sqrt(1 + u²/4) - 1)]` |

The prior four-penalty screen at the old Fixed lambda made pseudo-Huber `delta=2` the closest new candidate; mixed and window-log penalties were less competitive there. This bounded joint probe compared both loss arms at `lambda in {0.25, 0.5634538227695682, 1, 2}` on targets 1405, 2152, 1153, 1693 × seeds 42/43. The `0.563...` cells were reused from the earlier independently checked screen; all other cells were run fresh. Because the lowest two-seed macro was at the upper grid edge, the predeclared boundary check ran both arms at `lambda=4`. After this, only the leading `lambda=2` pairs were checked on seed 44 against the already saved MSE `lambda=0.563...` baseline.

## Observed Calibration MAE

Equal-cell macro MAE in kWh, four targets × seeds 42/43 (eight cells per pair):

| Fixed lambda | MSE | Pseudo-Huber δ=2 |
| ---: | ---: | ---: |
| 0.25 | 5.304313 | 5.299064 |
| 0.563454 | 5.271401 | 5.274009 |
| 1 | 5.234907 | 5.233493 |
| **2** | **5.225880** | **5.225647** |
| 4, boundary check | 5.241350 | 5.243007 |

At `lambda=2`, pseudo-Huber beat MSE at the same lambda by only `0.000233` kWh on seeds 42/43. Compared with the existing MSE `lambda=0.563...` pair, its two-seed macro gain was `0.045754` kWh, below the `0.05` kWh local promotion threshold; target 1693 worsened. Higher `lambda=4` did not improve the macro.

Seed 44 check (four targets, same Calibration dates): MSE `lambda=0.563...` was **5.253882** kWh; MSE `lambda=2` was **5.295832**; pseudo-Huber `lambda=2` was **5.294561**. Thus both lambda-2 pairs were worse on this seed. Across all three seeds, MSE `lambda=0.563...` was **5.265561**, MSE `lambda=2` was **5.249197**, and pseudo-Huber `lambda=2` was **5.248619** kWh. The pseudo-Huber pair's mean difference from the existing pair was **-0.016943** kWh, still below the practical threshold. At the same `lambda=2`, pseudo-Huber's advantage over MSE was only `0.000579` kWh; the observed difference from the existing pair comes chiefly from changing lambda. Target mean differences (candidate minus existing MSE pair) were `-0.033708` (1405), `+0.047521` (2152), `-0.142998` (1153), and **`+0.061414` (1693)** kWh. The gain is concentrated in target 1153 while target 1693 crosses the proposed harm limit.

**Interpretation:** the current pair remains the defensible choice for #99. The local grid suggests a target-dependent lambda tradeoff, not a robust single improved retention/λ pair. A target-specific lambda would need its own preregistered method and untouched assessment data; selecting it from these same origins would add selection bias. Seed 44 is a robustness check across seeds, not a temporal holdout.

## Artifacts and verification scope

- Worktree `D:\Đồ Án\.cache\issue99-retention-audit`, branch `feat/continuous-retention-99`.
- Main grid script `.cache/issue99-retention-lambda-grid-v1.py`: SHA-256 `15df44d336cb5d10f47dfef6e858d4a3c5a51d18e704cfb2f0725d34909a0bd0`; output `.cache/issue99-retention-lambda-grid-v1/summary.json`: `902879d40272f3b10ca54c4c5a2d6ab4006726c71ba063e90f5d4eafa755bf59` (48 fresh runs).
- Boundary script `.cache/issue99-retention-lambda-boundary-v1.py`: `5138264bac600109519a039cd050a5e825e6b0009bea3f3c8f3d721e66890270`; output `.cache/issue99-retention-lambda-boundary-v1/summary.json`: `e23cf305abd527477af5a86caf70e6c5563fe8d00ad4c0c9222590270a345171` (16 runs).
- Seed-44 script `.cache/issue99-retention-lambda-seed44-v1.py`: `9ada77807cae23114257b623884e3e6c622796bec613582e6f31151a40f45483`; output `.cache/issue99-retention-lambda-seed44-v1/summary.json`: `12c9b3332c3f2c973367ac4a59106874a1a8a5e2111b45409c1d59432a20bce8` (8 runs).
- Reused `lambda=0.563...` cells and seed-44 baseline: `.cache/issue99-retention-screen-v2/summary.json` and `.cache/issue99-retention-seed44-v1/summary.json`, with hashes in `issue99-retention-screen-20261110.md`.
- The input manifest and three Source10 checkpoint hashes are pinned in `configs/issue99-protocol-locked-v2.json`; each run uses the repository loader. Outputs are separate ignored run directories with daily tick events, metadata, and run IDs. No historical run or raw archive was overwritten.

The exploratory scripts patch the training and diagnostic retention imports in memory. Standard runner code identity and resume binding do **not** encode the loss arm; the script hash is required to interpret each run. No formal resume claim is made for these new penalties. `phase=pilot` produces a null official objective; all numbers above are independently derived from the 19 registered Calibration score events per cell. An independent read-only audit verified 48/16/8 run directories and 912/304/152 unique Calibration scores for grid/boundary/seed-44 respectively; recomputed MAE/RMSE matched every summary row within `1e-12`. It also checked all 72 run and binding records for run ID, lambda, frozen state, seeds, input/source and latent identities, and code commit. The diagnostic events use the matching loss after the patch, but they were not used to select a pair.

Commands run: Ruff check/format check and `python -m py_compile` on all three scripts before execution; `PYTHONPATH=. python .cache/issue99-retention-lambda-{grid,boundary,seed44}-v1.py` as three separate PowerShell commands; Python aggregation of the current and prior summaries; independent event recomputation; `python -m tools.check_release`; `git diff --check`. PyTorch emitted a non-contiguous GRU-weight performance warning; all 72 fresh runs completed. The full README unit suite was not rerun because tracked code did not change. No Kaggle job was submitted for this joint probe.
