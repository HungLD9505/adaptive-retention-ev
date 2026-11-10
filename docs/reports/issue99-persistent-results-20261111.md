# Issue #99: persistent λ follow-up, exploratory Development result

**Observed on Kaggle, 2026-11-11.** The six-run pilot and 48-run Calibration
matrix completed. Independent saved-vector and arrived-label verification
reported **PASS**. The locked promotion gate reported **FAIL**, so no Later
matrix was run. The Development cohort had been inspected previously; these
figures do not constitute an independent test result or a new Final result.

## Identity and output locations

- Kaggle notebook: [issue99-source10-2798384-paired-comparison-v2](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2).
  The executed package was pinned to commit `b2ab78b`; preserve the exact
  saved Kaggle version/run identifier in the final archive receipt. An earlier
  Version 4 at commit `087b7ee` was cancelled for interactive use.
- Runtime root: `/kaggle/working/issue99-persistent-b2ab78ba`.
  `results/` contains `pilot/`, `calibration/`, `pilot-independent-verification.json`,
  `calibration-gate.json` and `independent-verification.json`; `report/`
  contains the after-run tables and plots listed below. No `later/` result is
  authorized by this gate.
- Pilot run directories: `results/pilot/{fixed,persistent}-{1405-seed42,2152-seed43,1693-seed42}`
  (six total; 22 ticks each).
- Calibration directories: `results/calibration/{lambda0,fixed,immediate,persistent}-{1405,2152,1153,1693}-seed{42,43,44}`
  (48 total). Each run contains `run.json`, `binding.json`, initial-adaptation
  metadata and committed forecast/event/state ticks. These paths describe
  observed Kaggle output, not locally downloaded files.
- Protocol SHA-256: `f0443273e12eac8c0f8311e4e7b7ba2abd7bdc2a616a74d688bea442fcd96acb`.
  Embedded package SHA-256:
  `97cf995e84decb5e7725a7e5f5216a1281ae86df49a57e4983dd07e2c6c7faf0`.
  Calibration gate SHA-256:
  `ed4ddebcc1ba6eeb2189523c44692890a6804da07f09225772dc5f3367d956c2`.
  Independent verifier SHA-256:
  `b4e6854df92d1929958c8cb4ab1e1f8c0a570a4703eba9e8e26454b8cbe97c7b`.
- Runtime: Python 3.13.16, PyTorch 2.11/CUDA 13.0, T4. The focused 26
  tests passed in 14.36 seconds on Kaggle. Ruff was absent there, and the
  embedded package omitted README files needed by `check_release`; both full
  README and Ruff checks passed in [CI run 42858352451](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42858352451)
  on Windows and Ubuntu at `c0ef72c`. The actual experiment commit `b2ab78b`
  also passed [CI run 42862056327](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42862056327):
  Ubuntu ran 946 main tests (2 skipped), nine Fixed and 12 confidence tests;
  Windows ran 946 main tests (4 skipped) and the same README suites. Release
  checks, `pip check`, Ruff and formatting passed in both jobs; Ruff reported
  567 files already formatted. These are fixture/code checks, not MAE outcomes.

## Method and result

The persistent candidate starts from the same Source10 and target adaptation
as the Fixed arm. It clones a shadow Adam branch, evaluates a proposed λ on
future complete arrived-label pairs, and on acceptance transfers **only the
scalar λ** to the real branch. It does not transplant candidate weights, Adam
state or RNG. The Fixed anchor is λ `0.7984450067079901`; the four methods are
λ=0, Fixed, immediate controller and persistent controller. All use the same
registered Calibration origins and paired target/seed cohorts.

The implemented, preregistered proposal is

\[
\lambda_c=\operatorname{clip}_{[\max(0,\lambda_F-0.25),\lambda_F+0.25]}
\left(\lambda_t-\operatorname{clip}(211.29500343057222\,g_{A,V},-0.1,0.1)\right),
\qquad \lambda_F=0.7984450067079901.
\]

A consists of two older arrived-label days and V one newer arrived-label day.
The differentiable Adam proposal uses the incumbent state. The shadow branch
then persists through the same ordered labels. Acceptance requires five complete
paired outcomes, mean candidate-minus-real MAE below −0.01 kWh, at least four
wins and no paired harm above 0.05 kWh. Nine issued days without five complete
pairs expires a block; identical proposals skip it. These settings were not
changed after seeing Calibration. The loss remains MAE plus λ times the
Source-scaled latent MSE; no replacement loss was evaluated in this study.

Values below are original-unit daily forecast MAE (kWh). Each target mean gives
equal weight to seeds 42/43/44; the macro gives equal weight to all four
targets. Metrics were independently recomputed from saved 24-hour forecast
vectors and labels available at each recorded scoring time.

| Target | λ=0 | Fixed | Immediate | Persistent |
| --- | ---: | ---: | ---: | ---: |
| 1405 | 5.779810039 | 5.443160213 | 5.434146188 | 5.443160213 |
| 2152 | 6.262338352 | 6.386284954 | 6.400426400 | 6.386284954 |
| 1153 | 6.851597122 | 6.575362612 | 6.560545866 | 6.574888700 |
| 1693 | 2.880775359 | 2.922014755 | 2.880728283 | 2.922014755 |
| **Macro** | **5.443630218** | **5.331705633** | **5.318961684** | **5.331587155** |

The [12 target/seed Calibration cells](issue99-persistent-calibration-cells-20261111.csv)
give all 48 method MAEs, common scored-day counts and final Persistent λ.
They were transcribed from Kaggle `summary.json` as displayed in the console/UI;
the CSV is **not a byte-for-byte copy** of the Kaggle artifact. The independent
saved-run verifier supplies the metric integrity claim.

| Seed macro | λ=0 | Fixed | Immediate | Persistent |
| --- | ---: | ---: | ---: | ---: |
| 42 | 5.409807955 | 5.303295895 | 5.287560424 | 5.302940461 |
| 43 | 5.506180368 | 5.350712321 | 5.348043964 | 5.350712321 |
| 44 | 5.414902330 | 5.341108684 | 5.321280665 | 5.341108684 |

Persistent − Fixed macro MAE was `−0.00011847792538244306` kWh (equivalently
Fixed minus Persistent gain `+0.00011847792538244306`). Across the pilot,
no candidate was accepted and the real Persistent forecasts matched Fixed.
The pilot's actual Persistent and Fixed MAE were identical in each paired
case: 1405/seed 42 `5.317494026045832` kWh on 20 scored days,
2152/seed 43 `6.539141490475028` kWh on 21 scored days, and
1693/seed 42 `2.565132769086285` kWh on 21 scored days. These are pilot
trajectory scores, not the registered Calibration objective.
Across Calibration, 69 proposals produced 57 decisions: **1 accepted**, 56
rejected, zero timeouts, 297 arrived paired observations, 309 shadow update
steps and 12 pending proposals at the recorded end. Only target 1153/seed 42
finished at λ `0.898445` rather than `0.798445`; the other 11 cells kept the
anchor. Historical Fixed cell values matched all 12 new Fixed cells exactly;
the Fixed and immediate macro deltas against the historical reference were
reported as zero. This checks comparability of those arms, not effectiveness
of the new controller.

The sole accepted block was target 1153/seed 42, block 0, on
`2022-12-09` for origin `2022-12-08` (UTC+08:00). Its hypergradient was
`−0.0013670767657458782`; the proposed and adopted λ moved from
`0.798445` to `0.898445`. The candidate won four of five complete paired
days, with mean candidate-minus-incumbent MAE
`−0.025986895958582234` kWh and worst paired harm
`+0.0018692711989096722` kWh. The recorded real state digests were equal
immediately before and after the scalar decision:
model `87050979179666f7bf1597a6c7d28a05498f85668235229b9d2de6a2b42ad7cd`,
Adam `a94504d6616b249cf4f8f2fec502ea2c901dc0cfcbab0beac1fd0990190433c2`,
RNG `f47856cadca826d66740d20207bd6569111c320d5fc9156849e62af6c6701d31`.
The full Calibration trajectory advantage for that real target/seed cell was
about `0.001422` kWh MAE, measured over a different time window. It cannot
be divided by or equated to the five-day candidate advantage to infer a
causal transfer rate.

The worst daily **real Persistent minus Fixed** harm was
`+0.2507772313223926` kWh at target 1153/seed 42 on
`2022-12-28T00:00:00+08:00`. This is a daily diagnostic; the registered
Calibration gate limits **target mean** harm, not every real daily error.
The worst observed **shadow candidate minus incumbent** daily harm was
`+0.36647627814818406` kWh at target 2152/seed 44, in a rejected
candidate branch. This distinction matters: the shadow harm did not enter
the actual Persistent forecast trajectory or the external pilot trajectory
screen.

The registered gate requires at least `0.01` kWh macro gain over Fixed, no
target mean harm above `0.05` kWh, improvement in at least two of three seed
macros, Persistent/Fixed wall ratio at most `2`, and complete paired coverage.
**Macro gain and seed consistency failed**: observed gain was only
`0.00011847792538244306` and only seed 42 improved. The other reported checks
passed. The correct protocol action was to stop before Later; no Later or
Final metric is available for this variant.

## Uncertainty, cost and diagnostic artifacts

The after-run report contains 1,332 daily metric rows. Descriptive 95%
stationary-bootstrap intervals used 2,000 replicates, seed `20261110`, mean
block length seven calendar days, gap-aware blocks, and common resampled
origins for paired methods within each target/seed. Intervals are descriptive
for the inspected Development windows, not independent confirmation.
The same time indices are shared across seeds within each target. Targets are
resampled separately, so intervals may omit cross-target shared shocks. Blocks
restart at missing calendar days and phase boundaries, with no end-to-start wrap.

| Fixed minus method, macro kWh | Observed | Descriptive 95% interval |
| --- | ---: | ---: |
| Persistent | +0.000118478 | [−0.001610010, +0.001372389] |
| Immediate | +0.012743949 | [−0.011496125, +0.041311127] |
| λ=0 | −0.111924584 | [−0.259066253, −0.013055426] |

| Method | Total invocation wall (s) | Artifact bytes | Peak allocated VRAM (bytes) | Peak reserved VRAM (bytes) |
| --- | ---: | ---: | ---: | ---: |
| λ=0 | 20.569068258 | 12,404,983 | 88,648,704 | 94,371,840 |
| Fixed | 22.060813066 | 12,424,619 | 89,899,008 | 92,274,688 |
| Immediate | 67.789506932 | 12,536,237 | 89,899,008 | 92,274,688 |
| Persistent | 35.602717160 | 20,753,457 | 89,899,008 | 94,371,840 |

Persistent/Fixed total invocation wall ratio was `1.6138442882175836`.
Invocation time includes loading and warmup; Fixed ran earlier than Persistent,
so this ratio is an observed cost rather than a hardware-independent speed
claim.

The Kaggle `report/` directory contained these observed files:

| File | Bytes | Purpose |
| --- | ---: | --- |
| `run-costs.csv` | 21,153 | Per-run runtime, VRAM, event and step counts |
| `daily-errors.csv` | 185,690 | Recomputed original-unit daily MAE/RMSE |
| `lambda-timeline.csv` | 107,195 | Real λ at each issued forecast; candidate λ separate |
| `summary.json` | 6,463 | Cell, target, seed, macro and bootstrap summaries |
| `report.md` | 2,152 | Kaggle-generated compact summary |
| `calibration-daily-paired-difference.png` | 89,996 | Per-day paired difference plot |
| `calibration-persistent-lambda.png` | 86,178 | Real λ trajectory plot |
| `artifact-manifest.json` | 1,274 | File sizes and SHA-256 bindings |

The observed `artifact-manifest.json` SHA-256 is
`3e71e73f5e8f9a09a8ad0fcf5c8445db6f67787054292fcbfbe9ddb32ba1c745`.
These hashes were read/verified within Kaggle; the result files have **not**
been downloaded and rehashed locally. Quick Save of Version 5 with Output
failed with `502 UploadKernelSessionOutput`. The kernel remained alive at the
last observation. Only duplicate, reconstructible `stage/inputs` and
`verified-bundle` directories were then relocated from the three new roots
`087b7ee0`, `b2ab78ba`, and `3c6b3c7a` into
`/kaggle/temp/issue99-reconstructible-input-copies-b2ab78ba`; original
mounted input, Source weights, all run results, committed ticks, code and
reports remained in `/kaggle/working`. The map is
`/kaggle/working/issue99-persistent-b2ab78ba/reconstructible-input-relocations.json`.
Output size fell from about 3.1 GiB to 155.5 MiB on the Kaggle UI; the logical
working-file total was separately reported as 135,540,907 bytes. The final
Persistent 1153/seed 42 committed `tick-0028/state.pt` remained in working
storage at 1,464,155 bytes with SHA-256
`5d631f2dcc4c7197d153d9161602d6bad3466465a12fdd6deedccb4259daeed4`.
The verifier and report-manifest hashes above were unchanged after the move.
`stage/inputs` must be
reconstructed from the original attached ZIP with hash checks for any future
replay; `/kaggle/temp` is not durable. Quick Save Version 6, named
`b2ab78b verified54 compact output`, was submitted with Output and showed
**Committing** at the last observation. Durable saved Output remains **not
confirmed**. Preserve all notebook versions and output paths.

## Interpretation and next work

The λ-only transfer may be too conservative: a shadow branch can show a
candidate forecast gain, yet adopting its λ alone changes the real model's
subsequent updates without adopting the candidate weights or Adam state.
That coupling is a **hypothesis**, not established as the cause of the small
gain here. The observed 56 rejections and single acceptance show that the
locked acceptance rule rarely changed the real λ in this Calibration matrix.
Do not infer that a full branch transplant would improve results.

The next research step, if pursued, is a **new preregistered λ-only protocol**
that diagnoses rejected blocks, actual post-decision real-branch MAE, coverage
and threshold sensitivity on Development without selecting on Later or Final.
Any new rule needs its own independent verification and exploratory label.
For this locked protocol, preserve the failed gate and do not run Later.

Files changed for this result record: this Markdown report, its 48-cell CSV,
and the handoff and validation ledgers. No local data replay
or training command was run for this report. Repository links and command
history are in [the Kaggle handoff](issue99-persistent-kaggle-handoff-20261110.md),
[validation ledger](issue99-persistent-validation-20261110.md) and
[verifier notes](issue99-persistent-verifier-notes-20261110.md). The Kaggle
commands were the pinned notebook's focused tests, pilot, independent pilot
audit, Calibration dispatch, independent Calibration audit, gate and report
generator; exact invocations are embedded in `tools/issue99_persistent_notebook.py`.
