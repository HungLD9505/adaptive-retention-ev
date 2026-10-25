# Sprint 2 notebook and clean CPU reproduction report — 2026-10-25

## 1. Objective & Scope

Provide four readable notebook interfaces for #19/#20/#21/#39 using the existing core implementation. Validate their default execution from fresh kernels and an isolated environment; retain the completed representative matrix. This is engineering and execution evidence, with independent review and research effectiveness still open.

## 2. Methodology

| Notebook under experiments/hung_sprint2/notebooks | Role | Default behavior validated |
| --- | --- | --- |
| 01_model_transfer.ipynb | GRU/retention equations, Source/Target lineage, 24-hour inference and gradients | Load real checkpoints on CPU; forecast one actual Development input; backward without an optimizer step |
| 02_controller_runner.ipynb | Bootstrap LCB, chronology, decisions and recovery | Expected-value controller example; inspect real decisions; one real Development day in a temporary CPU runner with checkpoint restore |
| 03_development_execution.ipynb | Backend/device choice, fixed representative matrix and recovery | Read 216 stage manifests, display the new-run command; training opt-in remains off |
| 04_results_reproducibility.ipynb | Metrics, coverage, costs, integrity and plot | Recompute 354 checkpoint/journal hashes; inspect all 69 audited replay rows and coverage |

Notebooks import model, training, retention, controller, runner, checkpoint and loader modules. They do not copy the forecasting/controller implementation into cells. Existing Kaggle/Colab setup notebooks remain the platform entry points and are linked from notebook 03.

## 3. Implementation

Four new notebooks form the presentation interface. The existing, unexecuted Kaggle verification notebook received only Ruff formatting and removal of an unused os import; it had no recorded outputs to preserve. Its pinned code bundle, run identity and method settings were retained. Other historical notebooks were preserved.

No core module/config/selection change was made by this notebook work. The representative execution used commit a34a49e5f04920ef30456fe6c0ea56eb2f1d659a; final handoff code also includes the separately reported opt-in model RNG restoration fix. Notebook source links point to the actual modules rather than embedding copies.

## 4. Input

Default evidence root: runs/hung-39-representative-local-20261025T2103/. It contains matrix_identity.json, audit_summary.json, 216 completed stage manifests and their checkpoints/journals. Prepared Development inputs are under data/inputs/issue18-input-handoff-v1-20261019/; the first real 7-day input for entity 2264 is used in CPU examples. The shared tensor contract remains X_hist[B,24,7], C_future[B,24,5], Y_pred[B,24].

Every notebook checks the config and selection hashes against matrix identity. The inference notebook verifies Source and target checkpoint hashes and uses accepted loader readback; the results notebook independently verifies all 354 checkpoint/journal hashes. Missing required files fail explicitly. Final/test data are not used.

## 5. Configuration

Isolated environment: repo-local .venv-handoff, Python 3.13.7, torch 2.8.0+cpu. Python 3.13.7 is an explicit deviation from README's reference Python 3.12; a clean local Python 3.12 execution was not performed. The isolated environment does not inherit global site-packages or the global ultralytics/numpy conflict. It passed pip check.

Pinned presentation packages: nbformat 5.10.4, nbclient 0.10.2, ipykernel 6.29.5, pandas 3.0.1, matplotlib 3.10.8, plus requirements-dev.txt (Ruff 0.17.0) and requirements-model.txt. The exact transitive dependency inventory is in the validation run's requirements-observed.txt (including numpy 2.5.4). CPU PyTorch was installed from the official CPU wheel index; the existing CUDA installation was not modified.

Matrix evidence remains diagnostic config v1, selection v2, 7/14/28 days and seeds 7/11/19. Notebook 03 requires HUNG_EXECUTE_NEW_RUN=YES and an unused HUNG_NEW_OUTPUT_ROOT before launching training. Its default run recorded no matrix launch. Backend/device selection is displayed; the recorded local matrix identity and reported backend remain separate from a future remote execution.

## 6. Output

All four new notebooks contain actual outputs from their clean CPU validation. Validation artifact root: runs/hung-39-notebook-clean-cpu-20261025/. It contains validation.json, pip-check.log, full-tests.log, ruff-check.log, ruff-format.log, requirements-observed.txt and the repo-local kernelspec used to select .venv-handoff/Scripts/python.exe. The venv and validation artifacts are ignored by Git; Python's venv-generated .gitignore was checked. Temporary demonstration runner checkpoints are cleaned after readback and do not replace experiment checkpoints.

## 7. Experimental Results

| Clean isolated notebook execution | Time | Result |
| --- | ---: | --- |
| 01 Model/transfer | 13.770 s | PASS, CPU forecast shape [1,24], latent [1,64], finite gradients and frozen reference |
| 02 Controller/runner | 10.841 s | PASS, expected switch, causal one-day events and CPU checkpoint restore |
| 03 Execution interface | 4.570 s | PASS, matrix readback, execution opt-in off |
| 04 Results/integrity | 4.144 s | PASS, 216 stages, 354 hashes, 69 rows and coverage plot |

These durations measure notebook validation, not GPU matrix throughput. The existing representative matrix metrics, null cases, runtime and per-entity results are in the phase D report/evidence JSON. The notebooks read these values rather than recomputing model selection.

## 8. Correctness & Validation

- Isolated pip check: PASS, no broken requirements.
- Isolated full unit suite: 177 tests run in 15.144 s, PASS, two skipped (CUDA unavailable in the CPU wheel and a POSIX-only fixture). The separate CUDA environment's tests and hardware diagnostics are indexed by the parent phase reports.
- Isolated Ruff check and Ruff format check: PASS. Notebook syntax/schema validation with nbformat: PASS. All code cells executed sequentially in a new isolated kernel for each notebook; no error outputs remained.
- The results notebook retained null MAE/RMSE for zero-score rows and recomputed all checkpoint/journal hashes. The CPU restore example restores a temporary CPU runner; it does not resume the CUDA matrix on a different device.
- Windows emitted a non-fatal ZeroMQ selector-thread warning during kernel startup; execution completed successfully.

## 9. Discussion & Limitations

The clean CPU check establishes the four default notebook paths with actual local artifacts. It does not establish a fresh Python 3.12, Kaggle or Colab execution of these new notebooks; their platform preparation and future GPU opt-in remain instructions. A new environment must first acquire the identified inputs and run artifacts. Existing pinned platform verification evidence retains its original scope.

Correctness examples and successful execution do not demonstrate superiority over baselines, full-cohort coverage, accepted Source training sufficiency, an approved configuration or agreement with the independent implementation. No Final run, extra hyperparameter search or duplicated GPU matrix was launched for presentation validation.

## 10. Reproduction

The executed dependency commands were:

    python -m venv .venv-handoff
    .venv-handoff/Scripts/python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu -r requirements-model.txt
    .venv-handoff/Scripts/python.exe -m pip install -r requirements-dev.txt nbformat==5.10.4 nbclient==0.10.2 ipykernel==6.29.5 pandas==3.0.1 matplotlib==3.10.8

Set PYTHONUTF8=1, TEMP/TMP to the repository's .cache/testtmp, and HUNG_EXECUTE_NEW_RUN=NO. The recorded commands then ran pip check, unittest discover -s tests -q, Ruff check and Ruff format --check with the isolated interpreter; exact argv/status/durations are in validation.json. nbclient executed each notebook using timeout=300, kernel_name=hung-handoff-cpu, repository working directory, and a kernelspec pointing at that isolated interpreter. Notebook metadata is restored to portable Python 3 after execution. Set HUNG_REPO_ROOT, HUNG_RUN_ROOT and HUNG_INPUT_BASE when artifact locations differ.

Preserve completed artifacts and stop at technical handoff. A new training execution requires a new output root and verification purpose; resuming an experiment requires its original compatible identity.
