# #39 clean Python 3.12 notebook readback — 2026-10-26

## Objective and scope

Validate the four Sprint 2 presentation notebooks from fresh kernels under the README's Python 3.12 reference, while retaining the frozen representative Development matrix. This is CPU correctness and artifact readback, not a new training run or model-effectiveness comparison.

## Environment and provenance

- Source: the official [Python 3.12.10 Windows 64-bit full ZIP](https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.zip), 32,399,361 bytes, SHA-256 `8649692de846c56a7189d6dae5c322ab20deb1b5908b6f39426b62a36f39415d`.
- Extracted interpreter and all installed packages are under ignored repository path `.cache/python312/runtime/`. Python user-site access was disabled with `PYTHONNOUSERSITE=1`; `PYTHONUTF8=1` handled the Unicode repository path. A fresh-kernel probe confirmed Python 3.12.10, PyTorch 2.8.0+cpu, `site.ENABLE_USER_SITE=False`, and no `sys.path` entries outside the repository.
- The kernel spec is stored under `.cache/python312/jupyter/kernels/hung-handoff-py312/`. Temporary files, Jupyter runtime/configuration, IPython state, Matplotlib configuration, and pip cache were redirected into `.cache/python312/`.
- Installed the pinned `requirements-model.txt`, `requirements-dev.txt`, nbformat 5.10.4, nbclient 0.10.2, ipykernel 6.29.5, pandas 3.0.1, and matplotlib 3.10.8. The observed package inventory is `runs/hung-39-notebook-clean-py312-20261026/requirements-observed.txt`. `pip check` reported no broken requirements.
- Inputs were the accepted Development data under `data/inputs/issue18-input-handoff-v1-20261019/` and the unchanged representative run `runs/hung-39-representative-local-20261025T2103/`. The notebook code SHA-256 values and environment details are in `runs/hung-39-notebook-clean-py312-20261026/validation.json`.

## Executed validation

`nbclient` loaded each checked-in notebook from disk and executed it in a fresh `hung-handoff-py312` kernel with the repository as working directory, a 300-second cell timeout, and `HUNG_EXECUTE_NEW_RUN=NO`. Execution occurred in memory; the notebook source files and the original representative artifacts were not modified.

| Notebook | Code cells executed | Error outputs | Elapsed | Result |
| --- | ---: | ---: | ---: | --- |
| 01_model_transfer.ipynb | 4/4 | 0 | 15.468 s | PASS |
| 02_controller_runner.ipynb | 4/4 | 0 | 14.990 s | PASS |
| 03_development_execution.ipynb | 4/4 | 0 | 5.989 s | PASS; new-run opt-in off |
| 04_results_reproducibility.ipynb | 4/4 | 0 | 11.699 s | PASS |

The isolated Python 3.12.10 environment also passed `python -m unittest discover -s tests -q`: 177 tests, two skips, 21.517 seconds. `ruff check .`, `ruff format --check` on all 66 tracked Python/notebook files, and `git diff --check` passed. `python -m tools.sources list` ran successfully. A non-fatal Windows ZeroMQ selector-thread warning appeared during notebook kernel startup.

The broad `ruff format --check .` command reported one pre-existing untracked file, `experiments/hung_sprint2/kaggle_39_representative_runall.ipynb`, as unformatted. That unrelated draft was preserved unchanged and is not among the four validated notebooks or tracked PR files. The tracked-file format check passed.

## Remaining limits

This closes the clean Python 3.12 default-notebook execution gap recorded in the earlier Phase E snapshot. It does not establish Colab tensor/Drive handoff, a compressed Kaggle dataset ZIP download/local roundtrip, agreement with the independent implementation, approved Source/config methodology, peer review, or #39 acceptance. The local representative matrix and Kaggle T4 verification retain their separate run identities. No Codex usage reset was used.
