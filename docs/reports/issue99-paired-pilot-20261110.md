# Issue #99 paired counterfactual lambda pilot (10 November 2026)

## Scope and conclusion

This is an exploratory **local Calibration-only** screen of a new controller, not a scored Evaluation/Final result. The frozen pre-run rule is `.cache/paired-pilot-spec-v1.json`. The controller lowered equal-case mean MAE by only **0.000216 kWh** against Fixed across three selected target/seed cases. That is below the predeclared **0.01 kWh** screen threshold. Target 2152/seed43 worsened despite four accepted proposals. **Do not promote this variant to the full 4-target × 3-seed matrix or claim an effectiveness gain.**

Worktree: `D:/Đồ Án/.cache/issue99-paired-pilot`, branch `feat/99-paired-pilot`, based on PR #102 commit `302fb6b00a190c788ba3ffd81268ace52a151e8a`. The PR #102 runner's existing Fixed and immediate-controller behavior is retained by default. No historical run, Report 1 loss, Evaluation or Final artifact was changed.

## Method and frozen screen

The training loss remains normalized 24-hour forecast MAE plus lambda times Source-scaled latent MSE retention. At a block start, the existing A→V hypergradient proposes a bounded lambda. The real model keeps the incumbent lambda. For each of the next three complete paired W outcomes, a candidate branch and an incumbent branch start from the **same pre-V model, Adam and RNG snapshot**, update on the same arrived V record, and issue forecasts before W's label. The incumbent shadow must match the real forecast. Each candidate forecast is saved and bound to W's forecast artifact. Only after W's complete label arrives is its candidate-minus-incumbent 24-hour MAE computed. A proposal is accepted for future real updates if its three paired differences have median below `-0.01` kWh and at least two wins; a block with fewer than three valid pairs after seven issued days expires. Adopting only the scalar lambda does not transfer the candidate shadow's model/Adam state, so a favorable counterfactual forecast is not guaranteed to improve the later real trajectory.

Anchor Fixed lambda `0.7984450067079901`; proposal eta `211.29500343057222`, maximum absolute step `0.05`, trust radius `0.25`; block size `3`, maximum wait `7`. Predeclared cases: 1405/42, 2152/43 and 1693/42, first 22 daily ticks, paired registered Calibration origins only. The screen required equal coverage, mean MAE gain at least `0.01` kWh, no case harm above `0.05` kWh, and wall cost at most `2×` paired Fixed. These three cases are a feasibility/early-signal screen, not a basis for selecting a globally best controller.

Input: `D:/Đồ Án/.cache/issue99-retention-audit/.cache/issue99-input14`, manifest SHA-256 `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`. Source42: `D:/Đồ Án/.cache/issue99-retention-audit/.cache/issue99-local-gpu-source42-debug-v1/epoch-10.pt`, SHA-256 `a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b`. Source43: `.cache/source43/epoch-10.pt`, extracted without overwrite from the original Source ZIP and verified against its bundled SHA-256 `2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f`. The repository loader checked input/checkpoint compatibility in each run.

## Actual replay results

MAE below is the mean of the **same scored Calibration origins** for each arm, in original kWh. Delta is paired controller minus Fixed; negative means an improvement. `tools/issue99_paired_pilot_audit.py` independently reads score and paired events, checks origin pairing and candidate/incumbent arithmetic, and writes `.cache/paired-pilot-audit-v1.json`.

| Target / seed | Paired scored days | Fixed MAE | Paired-controller MAE | Delta | Proposals accepted / rejected | Final lambda |
|---|---:|---:|---:|---:|---:|---:|
| 1405 / 42 | 20 | 5.317494 | 5.316249 | -0.001245 | 3 / 2 | 0.891182 |
| 2152 / 43 | 21 | 6.539130 | 6.539727 | +0.000597 | 4 / 2 | 0.835534 |
| 1693 / 42 | 21 | 2.565125 | 2.565125 | 0.000000 | 0 / 6 | 0.798445 |
| Equal-case mean delta | | | | **-0.000216** | | |

No incumbent-shadow mismatch or block timeout was observed. Controller/Fixed invocation wall times were 10.894/8.646, 10.995/8.616 and 10.888/8.470 seconds, respectively, or about `1.26–1.29×`; these sequential times include loading and warmup and are descriptive. Peak allocated GPU bytes were 79,293,440/78,254,080; 84,994,560/82,060,288; and 84,994,560/82,060,288 (controller/Fixed). Controller virtual-step counts were 42, 45 and 45, including A→V proposal and paired shadow steps. All six runs finished successfully, each with 22 issued days and an immutable config/code/input binding and event commit chain.

Run directories, all under this worktree and never overwriting earlier outputs:

| Arm | 1405 / 42 | 2152 / 43 | 1693 / 42 |
|---|---|---|---|
| Fixed | `.cache/pilot-fixed-1405-42-v1` | `.cache/pilot-fixed-2152-43-v1` | `.cache/pilot-fixed-1693-42-v1` |
| Paired | `.cache/pilot-paired-1405-42-v1` | `.cache/pilot-paired-2152-43-v1` | `.cache/pilot-paired-1693-42-v1` |

Configs: `.cache/pilot-fixed-seed42.json`, `.cache/pilot-fixed-seed43.json`, `.cache/pilot-paired-seed42.json`, `.cache/pilot-paired-seed43.json`. Source and input data remain outside Git; each run's `run.json`, daily forecasts, events and checkpoints remain in the ignored run directories above.

## Commands, checks and outstanding work

The replay command was invoked separately for each of the six arm/case combinations, changing entity, Source, config and output as listed above. One exact example:

```text
python -m ev_runner.continuous_run --inputs ../issue99-retention-audit/.cache/issue99-input14 --manifest-sha256 66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9 --entity-id 1405 --source ../issue99-retention-audit/.cache/issue99-local-gpu-source42-debug-v1/epoch-10.pt --source-sha256 a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b --config .cache/pilot-paired-seed42.json --output .cache/pilot-paired-1405-42-v1 --device cuda --stop-after-ticks 22
python tools/issue99_paired_pilot_audit.py --root .cache --protocol docs/reports/issue99-study-20261110/protocol-lock.json --output .cache/paired-pilot-audit-v1.json
python -m unittest tests.test_issue99_paired tests.test_issue99_continuous_runner tests.test_issue99_hypergradient -v
python -m py_compile ev_control/paired.py ev_runner/continuous.py ev_runner/continuous_run.py tests/test_issue99_paired.py tools/issue99_paired_pilot_audit.py
git diff --check
```

The implementation agent's focused suite passed 17/17; an independent rerun of nine relevant tests passed 9/9 with `TEMP`/`TMP`/`TMPDIR` inside the worktree. They cover shadow equality, delayed label timing, earlier forecast immutability, three-pair acceptance, resume and pilot-only validation. No real-data run failed; PyTorch emitted a non-contiguous GRU weight performance warning. The README full suite and Ruff checks were not rerun: this machine has Python 3.13 rather than the README's Python 3.12 and the previous #99 pilot's full 940-test run failed largely on Windows cp1252/Unicode-path and symlink-permission issues; Ruff was not installed. These gates remain open before an integration PR.

**Next step:** analyze why accepted local counterfactual proposals on 2152/43 did not improve the real trajectory, including λ trace and delayed paired differences. Any new controller rule must be versioned and tested on Calibration without using later Evaluation/Final results for selection. A positive bounded screen would still require the complete 4-target × 3-seed Calibration comparison and cost audit before locking a full protocol. No full Kaggle run is authorized by this pilot's evidence.
