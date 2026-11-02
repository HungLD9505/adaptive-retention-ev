# Phase E — Reproducibility, technical handoff and execution freeze

## 1. Objective & Scope

Hand off the completed #39 diagnostic Development implementation and artifacts so another person can inspect or reproduce them without an active notebook session. Technical evidence is separated from configuration/method approval, independent comparison and issue acceptance. Final/test and #22/#23 experiments remain outside this handoff.

## 2. Methodology

Verification used a fresh full stage/hash audit, independent serialized-state/journal readback, metric recomputation from stored tensors, bounded CUDA recovery, archive CRC and member SHA checks, fresh notebook kernels, and a clean CPU environment check. Platform inspection/upload used signed-in browser sessions; displayed runtime metadata is distinguished from tensor-level CUDA verification.

## 3. Implementation

The representative matrix executed commit `a34a49e5f04920ef30456fe6c0ea56eb2f1d659a`. Its exact config, selection, input hashes and executed-source map are frozen in matrix identity and [machine-readable evidence](hung-39-representative-local-20261025-evidence.json); backend is explicitly **local**.

Post-run code adds optional model-checkpoint RNG snapshots and `load_checkpoint(..., restore_rng=True)`, preserving legacy/default transfer loads. Newly saved snapshots reject incompatible device/environment on explicit RNG restoration. Old matrix Source/target checkpoints have no RNG snapshot; their original completed artifacts remain unchanged. The runner checkpoints already contain CPU/CUDA RNG. Four thin notebooks import core code, display real artifact readback and keep GPU matrix execution opt-in. The previously unexecuted Kaggle notebook received an unused-import/format cleanup.

## 4. Input

Use the fixed DATA-v1 UrbanEV SZH ZIP and all three budget directories under `data/inputs/issue18-input-handoff-v1-20261019`. Hashes, accepted tensor/mask/scale identities and release provenance are in [Phase 0](hung-39-phase0-environment-20261025-masterplan.md) and [Phase D](hung-39-representative-local-20261025.md). Source/Development only were consumed. Downloading a matching file name is insufficient; verify bytes and manifests before use.

## 5. Configuration & Environment

Matrix: Python 3.13.7, PyTorch 2.8.0+cu126, CUDA 12.6, RTX 3050 Ti Laptop GPU, seeds 7/11/19, diagnostic config v1 and selection v2. The actual loaded runner model was verified on `cuda:0`; the GPU name alone was not used as proof.

The global execution environment has an unrelated ultralytics/numpy dependency conflict. A new isolated `.venv-handoff` with Python 3.13.7, PyTorch 2.8.0+cpu and declared notebook dependencies passed `pip check`, all 177 tests (2 skips), Ruff and all four notebooks in new kernels. The [notebook validation report](hung-39-notebook-validation-20261025-masterplan.md) records exact commands, versions and timings; logs and the observed dependency freeze are in `runs/hung-39-notebook-clean-cpu-20261025/`. README's exact Python 3.12 environment and a fresh remote GPU notebook run remain distinct from local Python 3.13 validation.

## 6. Output & Retrieval

| Evidence | Location |
| --- | --- |
| P0/A/B/C reports | `hung-39-phase0-environment-20261025-masterplan.md`, `hung-39-phase-a-model-transfer-20261025-masterplan.md`, `hung-39-phase-b-controller-20261025-masterplan.md`, `hung-39-phase-c-runner-20261025-masterplan.md` in this directory |
| Representative results + 69 cell records/SHA inventory | [Phase D report](hung-39-representative-local-20261025.md), [evidence JSON](hung-39-representative-local-20261025-evidence.json) |
| Four executable presentation/readback notebooks | `experiments/hung_sprint2/notebooks/01_model_transfer.ipynb` through `04_results_reproducibility.ipynb` |
| Complete local run | `runs/hung-39-representative-local-20261025T2103/` |
| Complete local archive | `runs/hung-39-representative-local-20261025T2103.zip` |
| Durable cloud copy | [Private Kaggle dataset, Version 1](https://www.kaggle.com/datasets/hungluongduc/hung-39-representative-local-20261025t2103) |
| Bounded model RNG recovery diagnostic | `runs/hung-39-model-rng-readback-20261025T2330/readback.json` and derived checkpoint |
| Platform/quota/probe evidence | [Platform report](hung-39-platform-readiness-20261025T2325.md) |
| Notebook and isolated-environment evidence | [Notebook validation report](hung-39-notebook-validation-20261025-masterplan.md) |
| Final code/notebook/dependency freeze | `hung-39-freeze-20261025.json` in this directory |

Local ZIP SHA-256: `7d74ec06f9102d1a7357da380bc252570cab2a817a9fcce48030f89c3311f2fa`, 249,622,687 bytes. All 573 ZIP members passed CRC and byte-hash readback. Kaggle automatically extracted it into 573 run members plus the integrity sidecar, 574 files total. The dataset is private and requires account access. Cloud download/member-hash roundtrip was not performed because the supported browser download interface could not select a destination inside the repo.

## 7. Experimental Results & Capacity

The matrix completed 216 stages/69 cells: 9 Source, 69 target, 138 replay. Total observed wall span was 4,054.25 s (67.57 min); summed stage CLI time 2,944.40 s. Source used 65,888 examples per stage, 31.17–60.42 s. Largest PyTorch CUDA allocation was 81.19 MiB; archive size was 249.62 MB. Detailed per-candidate/audit calls, updates, timing and state memory are retained in manifests and cell records.

For capacity planning, **one identical current-method sweep** measured approximately 1.13 local wall hours. Fourteen identical-cost sweeps would be about 15.77 hours as arithmetic budgeting only; nine baseline/five ablation implementations have different training and inference costs and were not benchmarked here. Source reuse, cohort size and platform behavior also differ. The displayed Kaggle quota of 27h34m is therefore not proof that Sprint 3 fits. Measure each approved adapter before making a full #22/#23 forecast.

## 8. Correctness & Validation

- 216/216 stage identities and 354/354 checkpoint/journal hashes passed; no missing cell.
- 138 serialized replay states, 20,394 forecast tensors and 18,313 journal events matched their manifests.
- All 69 live metrics were independently recomputed; 33 null cells stayed null; largest error difference was 3.55e-15 kWh.
- A real replay checkpoint restored CUDA model/optimizer, cursor and identical CPU/CUDA RNG.
- New model-RNG recovery saved a separate derived Source checkpoint without training; next CPU/CUDA draws, model weights, Adam state and scale matched. Old matrix model artifacts remain legacy snapshots.
- Final global unit suite after the RNG fix: **177 tests passed, 1 skipped**. Ruff lint/format and `git diff --check` passed after notebook/report formatting.
- Isolated CPU environment: `pip check`, 177 tests (2 skips), Ruff lint/format and all four notebooks passed. Notebook times were 13.77, 10.84, 4.57 and 4.14 seconds; matrix launch stayed opt-in/off. These are CPU inference, correctness and artifact readback executions, not a duplicate training matrix.

## 9. Discussion & Remaining Gates

Correctness fixtures, executed Development evidence and model effectiveness are separate claims. There is no baseline superiority claim. Source-only zero-score coverage was traced to incomplete 24-hour labels; six additional adaptation-null cells for entity 1987 were identified, with exact coverage in Phase D.

Kaggle saved verification Version 1 now has independently observed successful T4 UI metadata. Current quota was visible, but no new Kaggle GPU matrix was launched. Colab briefly displayed a T4 connection, then the disposable probe was blocked by session/reCAPTCHA errors; actual current tensor CUDA and Drive checkpoint handoff remain unverified. Unrelated user sessions were preserved. These platform limits do not invalidate the local run, and are retained as explicit unfinished verification.

Open acceptance work: Qyroven comparison, Source-pass/config review, peer approval, integration and acceptance of #39. The exact README Python 3.12 clean environment, Colab tensor/Drive handoff, cloud download roundtrip and future remote execution require their stated evidence before being marked complete.

## 10. Reproduction, Recovery & Freeze

Read Phase D for the exact matrix command and hashes. To reproduce or resume its historical identity, use commit `a34a49e` with the original CUDA environment and matching artifacts. New handoff code deliberately has different source hashes, so it must not be substituted into the old driver identity. A new backend, configuration, code or incompatible device requires a new execution root.

The representative run hashed the local selection v2 JSON with CRLF line endings (`840ea198...`), while the repository Git blob has LF endings (`273858df...`). The content is otherwise byte-equivalent: replacing each LF with CRLF in the Git blob reproduces the recorded SHA-256. Verify the reconstructed bytes before historical resume; using a clean checkout's LF file directly changes the execution identity. The freeze manifest records both hashes.

The four notebooks resolve the repository/input/run roots and display actual stored results. Run their default cells for inspection and correctness examples; enable matrix execution only for an explicitly assigned new verification objective. Source/target interrupted-stage training resume is not implemented by the matrix CLI; complete-stage reuse and replay 42→90 resume are the supported paths. Newly saved model RNG snapshots provide explicit state restoration, not an automatic CLI resume policy.

**Execution freeze:** representative training is complete. This handoff starts no further training, hyperparameter search, Final evaluation, baseline/ablation work or periodic monitoring. Preserve existing datasets, checkpoints, reports and runs. Read-only integrity inspection remains available. PR #46 receives only executed evidence; #39 stays open for review.

Files changed for this handoff: `training.py`, `tests/test_hung_training.py`, the existing unexecuted `kaggle_39_verification.ipynb`, four new notebooks listed above, the six phase reports (P0/A/B/C/D/E), platform and notebook validation reports, representative evidence JSON and final freeze JSON. The historical untracked selection draft is excluded from the commit. The Git commit inventory supplies the exact repository paths.
