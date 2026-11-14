# Issue #99 technical handoff — paths, run evidence and next actions

Snapshot checked on **10 November 2026** (Asia/Ho Chi Minh City). This snapshot indexes the execution paths and linked full-precision evidence. This record distinguishes bytes held in this Windows worktree from results read only on Kaggle or reported from another machine. No historical archive, checkpoint or run was overwritten.

## Repository and status

| Item | Identity and current interpretation |
| --- | --- |
| Worktree | `D:\Đồ Án\.cache\issue99-retention-audit` on `feat/continuous-retention-99`; the original `D:\Đồ Án` checkout remains on `main` and was not edited for #99. |
| [Issue #99](https://github.com/HungLD9505/adaptive-retention-ev/issues/99) | Open; its body marks 17/17 acceptance items checked under the separate PR #102 execution. Controller superiority is not an acceptance requirement. |
| [PR #100](https://github.com/HungLD9505/adaptive-retention-ev/pull/100) | Open into `dev`; exploratory protocol v2, HEAD `f00c820b3a1a73089958242cba28420747e222d1` before this handoff commit. [Foundation CI run 42715239023](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42715239023) **succeeded**. A new handoff commit will create a new HEAD/CI run; check that before integration. |
| [PR #102](https://github.com/HungLD9505/adaptive-retention-ev/pull/102) | Open; broader, different protocol. HEAD `71234eb1b217203f81425c44facbd8ccb83ed8be`, CI [run 42705043476](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42705043476) succeeded. Its metrics must not be pooled with PR #100. |
| [PR #103](https://github.com/HungLD9505/adaptive-retention-ev/pull/103) | Merged verifier hardening into PR #102 HEAD. The preserved raw archive has **not** been rerun through that hardened verifier in this workspace. |

The team lead authorized execution without an additional approval checkpoint. `AGENTS.md` and `docs/WORKFLOW.md` still describe the repository integration process; no PR or issue was merged/closed here. Do not use Final or already inspected Evaluation outcomes to select λ or controller settings. All current #99 outcome claims are exploratory Development evidence.

## Tracked files to read or run

Paths in this table are relative to the worktree above, so they also work in another clone.

| Purpose | Files |
| --- | --- |
| Local gate and exact input/Source hashes | `docs/reports/issue99-local-gate-20261110.md`, `docs/reports/issue99-local-audit-v2.json`, `tools/issue99_local_audit.py` |
| Locked PR #100 protocol and study profiles | `configs/issue99-protocol-locked-v2.json`, `configs/issue99-comparison-lock-v2.json`, `configs/issue99-fixed-search-v1.json`, `configs/issue99-study-calibration-v1.json`, `configs/issue99-study-evaluation-v1.json` |
| Model/controller/runner | `ev_control/hypergradient.py`, `ev_control/continuous.py`, `ev_control/diagnostics.py`, `ev_runner/continuous.py`, `ev_runner/continuous_run.py` |
| Kaggle transport and verifiers | `tools/issue99_kaggle_package.py`, `tools/issue99_kaggle_comparison_v2.py`, `tools/issue99_kaggle_readback_v2.py`, `ev_search/comparison.py`, `ev_search/comparison_verify.py` |
| Pilot, Fixed and paired evidence | `docs/reports/issue99-t4-pilot-20261110.md`, `docs/reports/issue99-fixed-search-protocol-v2.md`, `docs/reports/issue99-fixed-audit-protocol-v2.md`, `docs/reports/issue99-paired-comparison-protocol-v2.md`, `docs/reports/issue99-paired-readback-kaggle-v1.md` |
| Controller assessment and next gate | `docs/reports/issue99-controller-followup-20261110.md` |
| Focused fixtures | `tests/test_issue99_*.py` (16 files; discover with `-p 'test_issue99*.py'`) |

The scorer code used by the saved PR #100 Kaggle runs was commit `27983845b5d446e3915b0b4353570466f1da23ef`. Protocol v2 SHA-256 is `f104d8809e04d0cde7d8982efd8146788f32c3c9a1c561ee9309891e6b040eb0`; comparison lock SHA-256 is `209102126ca696c5da2e959b053cc413d0e8d59fda3f92b30168a7a483577269`. The v1 protocol's `+07:00` origin strings caused six null Fixed trials; v2 preserves the intended instants using input/replay `+08:00` strings. Preserve the failed v1 ledger and do not combine it with v2.

## Local data and ignored artifacts

All local paths below are within `D:\Đồ Án\.cache\issue99-retention-audit`. The parent directory `D:\Đồ Án\.cache\issue99-source-duration` was the originally recorded location of the three Source ZIPs; it was not reopened for this handoff. Use the copies and fingerprints below or rerun the gate before a new scored execution.

| Path under worktree | Contents and status |
| --- | --- |
| `.cache/issue99-kaggle-bundle-2798384-v1/` | Saved transport ingredients, `manifest.json` SHA-256 `a09f6a03ae5911717fd5afd070e93b52e0a3a066398278dac7b598bfd89ae088`. `issue99-code.zip` 7,925,193 B SHA `d2c6c24efa465ab23eb55716e121f43056d31255ab03eab41c436f3ff06f1754`; `inputs-urbanev-SZH-v1.zip` 151,254,390 B SHA `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. It also has `preflight.py` and the three ZIPs below. |
| `.cache/issue99-kaggle-bundle-2798384-v1/qyroven-issue23-source-duration-20261026-v1-seed42.zip` | 6,057,130 B; SHA `ed9ae3be074332a987b2964fa46b441c4bf696e94219dc218d1cb8b2561d7924`. |
| `.cache/issue99-kaggle-bundle-2798384-v1/qyroven-issue23-source-duration-20261026-v1-seed43.zip` | 6,104,459 B; SHA `ab1711327555c7f30c383e8e85fdd47358b3e7cc1b85b34f625f381b67b3ef50`. |
| `.cache/issue99-kaggle-bundle-2798384-v1/qyroven-issue23-source-duration-20261026-v1-seed44.zip` | 6,087,680 B; SHA `f07904e93e27b0d9d79a27f6b9cd64d33310d1d100f070aecd0d841f25561656`. |
| `.cache/issue99-kaggle-transport-2798384-v1.zip` | Complete transport ZIP, 177,450,555 B, SHA `07a3c7076844f55ce1058b34b99c4873ed53a0ced5e4fea2d591104a8a180cfe`. |
| `.cache/issue99-input14/` | Extracted 14-day `manifest.json`, `entities.jsonl`, `forecasts.jsonl`, `labels.jsonl`, `schedule.jsonl`, `training.jsonl`; manifest SHA `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`. Exact five member hashes are in `issue99-local-audit-v2.json`. |
| `.cache/issue99-comparison-stage-local-v2-preview/` | Staged `code/`, `inputs/`, `sources/seed{42,43,44}/epoch-10.pt`, `runtime.json` for local inspection. Source checkpoint SHAs: seed 42 `a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b`; 43 `2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f`; 44 `6f475e54768322c5b51f5837d6ce7e863cb9ef6d33aec05b4a1c2468cd0285a5`. |
| `.cache/issue99-audit-extracted/` | Separately extracted seed 42/43/44 epoch-10 checkpoints from the local audit; preserve. |

Local gate **PASS**: ZIP hashes/CRC, five 7-day and 14-day input files, strict checkpoint/model/Adam/latent metadata, and 65,888 Source training rows compared in order. The Source population identity was `c77778935190a7acd3cc00c35d7940a5c9bd59fa3dc0dca14b86505ead87b760`. The four targets 1405/2152/1153/1693 have 90 scheduled days; full-replay issued/scored counts later measured were 90/89 for 1405 and 59/52 for the other three. The input status is `technical_success_with_coverage_limits`; underlying publisher raw physical lineage was not reaudited during this review.

## Saved Kaggle executions and outputs

| Stage | Saved location, result and identity |
| --- | --- |
| [T4 pilot](https://www.kaggle.com/code/hungluongduc/issue99-source10-t4-pilot-20261110-v1?scriptVersionId=367782247) | Saved Version 2, run `367782247`, Tesla T4, 1405/seed42/20 ticks: 20 issued, 18 scored, 17 decisions, 19.0567 s invocation, peak allocated 87,919,616 B; objective deliberately null. Runtime Python 3.13.16, Torch 2.11.0+cu130, CUDA 13.0. |
| [Fixed search v2](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-fixed-search-protocol-v2) | 14 finite Calibration trials completed on T4 x2; search loop 916.995 s, Kaggle version 967.7 s. `issue99-fixed-search-protocol-v2.md` was written before the later verifier/selection, so its old “pending” heading is superseded by the next row. |
| [Independent Fixed verifier E](https://www.kaggle.com/code/hungluongduc/issue99-fixed-protocol-v2-independent-audit-e-v1) | PASS/14 from a separately authenticated 51-file package; verification JSON SHA `233f893338b41e1ac39da9cd0b79b56ad70fa4c86f024900de4ad6dc8fde991e`. The earlier verifier D lacked an import and produced no verdict; preserve that failed attempt. |
| [Calibration-only Fixed selection](https://www.kaggle.com/code/hungluongduc/issue99-fixed-selection-protocol-v2-v1) | Registered 0.05 kWh equivalence rule selected λ=`0.5634538227695682` from trial 13 before Evaluation; selection JSON SHA `5d7f834ff6ad4c36d328516e24a25ca2968b67fdc1c068b99aa0b0f7750bf3cb`. The old report marked the saved selection notebook pending; check its current saved status before claiming an additional saved audit. |
| [Paired comparison v2](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2) | Saved Version 1, run `367824175`: 60/60 jobs, 4 targets × 3 seeds × five methods, every cell 28/28 Evaluation origins. Original `verification.json` SHA `c3038079cd65f575851dfd53be139017c6ad95aad087d7a3817dcd34a3d6bfed`; Kaggle runtime 777.4 s, output 3,910,165,244 B. |
| [Independent Kaggle CPU readback](https://www.kaggle.com/code/hungluongduc/issue99-protocol-v2-paired-readback-v1?scriptVersionId=367837806) | Saved Version 1, run `367837806`: **PASS/60**. It checked code/Source/input identity, receipts, event/commit hashes, chronology, arrived labels, MAE/RMSE and 28/28 coverage using tracked `tools/issue99_kaggle_readback_v2.py` SHA `f7cbb5ebdd570e5e552beaab48221743985f3f34ae00aba8cfc3d4dcd05885bc`. Readback JSON SHA `d34af73570dce903d99b6d8961d3f11187e88f7b6293be5f280be4f8b4e2a0d6`, receipt-index SHA `a61d43f9e48512ddb5c7d7b62dd2b3eccc2ef267817636460ca45561072bb696`; CPU viewer runtime about 16m40s. |

PR #100 paired equal-target macro MAE in kWh: λ=0 `5.0773891674`, Fixed `4.9414314981`, old discrete `4.9723502743`, continuous Adam `5.0708594518`, frozen λ=0.1 `5.0531734402`. Continuous − Fixed is **+0.129428 kWh**. The 12 recorded run wall times summed to Fixed `94.564363` s and continuous `212.988075` s (`2.25×`). These numbers were independently recomputed inside Kaggle; the 3.91 GB output has **not** been downloaded or byte-audited locally. Browser output download was denied and the owner said a manual transfer was unavailable at that time; reading the mounted output inside Kaggle was the allowed fallback.

PR #102 reports a **different** later-window macro MAE: λ=0 `4.868597`, Fixed `4.803054`, old discrete `4.798259`, continuous `4.806223` kWh, so continuous − Fixed is **+0.003169 kWh**. Its 264,510,116-byte archive SHA-256 is `20f9e9ef62a9264209318348820fa2774f209ef2293398a94dda62e891722f6e`, reported verified on the author's Mac at `/Users/quyenmanh/Developer/TFL-EV/runs/issue99-study-20261110-v1/delivered/issue99-study-results-v1.tar.gz`. The 897,866-byte teacher review ZIP SHA is `82ecd771e3f213617f16a1a841aa05be9fe5f7f55806830ede6253362e9b3be2`, recorded at `/Users/quyenmanh/Developer/TFL-EV/runs/issue99-study-20261110-v1/issue99-teacher-review-v1.zip`. Neither file is present or independently checked in this Windows worktree. PR #102's verifier hardening at HEAD requires a fresh run on the preserved archive.

## Local controller probes (ignored, not Kaggle results)

All probes used the local RTX 3050 Ti, authenticated 14-day input and Source10 checkpoints, new output directories and arrived labels. Scripts are `.cache/issue99-controller-probe-v1.py`, `-v2.py`, `-v3.py`; output folders of the same base names contain each run's `run.json`, daily `tick-*/forecasts.json`, `events.jsonl`, state checkpoints and `summary.json`. Preserve these paths. Each probe used `phase=pilot`, `protocol_sha256=null`, `objective_origins=[]`; metrics below were filtered post-run to the registered 19 Calibration origins, so these are diagnostics, not protocol-bound scored trials.

| Probe | Script SHA-256 | Summary SHA-256 | Actual result |
| --- | --- | --- | --- |
| v1, 2 targets × seed42 × 3 arms | `e8054f607b123c24985db92a7d3d34e3677fc27c264de26153bfe1bb3e18d71d` | `3d76fd02aec83b6b07ea32225f227c587f60e907b0bd79162edb70a09d5cf3f2` | Old λ0.1/η0.01 barely moved; starting at Fixed λ with η100 helped target1405 slightly (MAE 5.336635→5.330351) but harmed 1693 (2.375795→2.440518), with two bound hits and final λ≈6.46. |
| v2, 2 targets × seed42 × 2 arms | `5efc322054a3011b12eaea8fb4cf60501ffdb974c1686d3803314d23a3d725d0` | `d1008794da96e7263667cdf7efd341bfe06413c7ccec95da5978013329af548e` | η10 improved both samples slightly; η30/bound2 harmed target1693. This is screening, not selection evidence. |
| v3, 4 targets × 3 seeds × paired Fixed/η10 | `fc93c9fcd03237fd166d05dc38a3b8a90aabfd15a1001f8396291780e11e32b9` | `e395237ef1767101f425ae12ab49c21c6ded71ab210bac28a20e569aff98f42d` | 24/24 runs completed; 19/19 Calibration scores per run (456/456), 498 full-replay score hashes matched saved forecasts, 225 controller decisions verified, zero bound hits. Fixed macro MAE `5.2655613743`; η10 `5.2642334933` (gain `0.0013278810` kWh). Target 2152 worsened `0.017436` kWh. Sum run wall time `49.695` vs `95.732` s (`1.93×`). |

The v3 gain is far below the existing 0.05 kWh practical-equivalence tolerance. It did **not** pass the proposed Kaggle promotion gate; no new Kaggle job was started. The independent local probe audit recomputed metrics from score events and checked score/forecast hashes, but did not reconstruct errors from raw label vectors. See `issue99-controller-followup-20261110.md` for per-target differences and the causal A→V versus V→future concern. No Final outcome was used for tuning.

## Verification commands and known failures

The last local follow-up ran `python -m py_compile` on the three ignored probe scripts, then `python .cache/issue99-controller-probe-v1.py`, `-v2.py`, `-v3.py` with `PYTHONPATH` set to the worktree. `Get-FileHash` pinned script and summary bytes; a separate Python aggregation read v3's 24 rows. `python -m tools.check_release` passed (17 report files and 92 historical source pins). `python -m unittest discover -s tests -p 'test_issue99*.py' -v` passed **72 tests**; `experiments/fixed_adaptation` passed 9 and `experiments/confidence_controller` passed 12. Ruff check and format passed using the installed ignored `.cache/issue99-ruff-0170` package; `git diff --cached --check` passed. The local global Python did not have Ruff on its default module path.

The full `python -m unittest discover -s tests -v` ran **964 tests, 2 skips, 3 errors** while the follow-up report was untracked. Two proxy-calibration fixture errors were caused by their clean-worktree gate and both passed when rerun after commit. The remaining `test_release_check` error was Windows `WinError 1314` (this process cannot create a symlink); the entire suite was not repeated. PyTorch also emitted a non-contiguous GRU-weight performance warning during local GPU runs. No #99 test failure was observed. Distinguish these local results from remote CI and scientific outcome evidence.

## What the next task should do

1. Check the current issue/PR/CI status; this snapshot's CI state can become stale. Keep PR #100 and PR #102 protocol identities separate. PR #102 is the candidate canonical #99 result because it has the broader matrix and smaller author-verified archive; failure to beat Fixed is a valid outcome.
2. Obtain or mount **the exact PR #102 archive** without overwriting any prior bytes. Run the hardened verifier at PR #102 HEAD against it and record manifest, run receipts, metric recomputation and failures. If the archive cannot be accessed here, state that gap rather than equating CI fixtures with a raw-artifact audit. PR #100's Kaggle output may remain an on-platform verified, locally unavailable supplementary study.
3. Reconcile code and protocol differences before integration into `dev`, retaining all null/unfavorable outcomes. The owner has waived an extra permission/review stop; follow the repository's branch/merge requirements otherwise. Close #99 only when the selected code/evidence is present on `dev` and the issue's remaining integration work is complete.
4. Treat controller improvement as a **separate exploratory v3 ablation**. First diagnose target2152 and whether the one-day A→V hypergradient predicts later forecast benefit. Lock exact comparator, candidates, seeds/cohort, causal windows, null handling and cost before further search. A proposed gate is complete 4×3 Calibration coverage, at least 0.05 kWh macro gain, no target mean harm over 0.05 kWh and ≤2× Fixed wall cost. The η10 probe fails the gain gate, so do not launch a Kaggle matrix from it. If there is no truly uninspected Development evaluation population, report all subsequent comparisons as exploratory.
