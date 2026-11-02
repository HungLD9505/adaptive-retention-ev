# #39 post-freeze validation — 2026-10-26 ICT

This supplements the frozen Development handoff at commit `4dd51b547cb37f5b665110d1d9eaf558f4d93fee`. No model code, configuration, selection, checkpoints, forecasts, or historical run outputs were changed. No training or Final/test evaluation was started.

## Python 3.12 CI evidence

The [PR #46 Actions run](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40213510034) checked out merge commit `24488af027e35a413a5cb4b2d114a3e911113a1e` for head `4dd51b5`. The workflow `.github/workflows/ci.yml` installs `requirements-dev.txt` and CPU `requirements-model.txt`, then runs `pip check`, source listing, all unit tests, Ruff lint/format, and `git diff --check`.

| Job | Python | Dependency check | Unit tests | Lint/format | Result |
| --- | --- | --- | --- | --- | --- |
| [Ubuntu 24.04](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40213510034/job/121229605857) | CPython 3.12.15 | No broken requirements | 177 passed, 1 skipped | Passed | Success |
| [Windows latest](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40213510034/job/121229605740) | CPython 3.12.10 | No broken requirements | 177 passed, 2 skipped | Passed | Success |

The job logs, not merely the green PR badge, provide the versions and test counts. CI did not execute the four presentation notebooks or train a Development matrix. Their clean-kernel execution remains evidenced separately on Python 3.13 CPU.

## Colab runtime probe

The existing Colab Development notebook displayed a connected Python 3 Google Compute Engine backend with **T4 (Python 3)**. A disposable playground was opened; it explicitly stated that changes would not be saved. A bounded CUDA model/tensor probe was prepared without running historical notebook cells. The playground connection did not succeed and displayed **"Could not connect to the reCAPTCHA service"**. The probe cell did not execute, so tensor/model CUDA placement and a new Drive checkpoint handoff are still unverified. The disposable tab was closed. The observed T4 allocation does not establish a successful workload or available sustained quota.

## Archive and acceptance limits

The private Kaggle representative dataset page showed Version 1 and 574 extracted files, consistent with the earlier upload report. No cloud download/member-hash roundtrip occurred in this follow-up. The local archive CRC and SHA readback remain covered by the frozen handoff. Peer review, independent comparison, configuration approval, and #39 acceptance remain open; PR #46 stays draft.
