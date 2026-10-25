# #39 Kaggle verification transition — 2026-10-25

Status: **prepared, not executed on Kaggle**. This is a proposed GPU alternative after Colab refused a GPU backend because of account usage limits. It does not change the Development protocol or establish team acceptance of Kaggle in place of Colab.

## Feasibility checked

- The signed-in Kaggle account showed phone verification complete and `Kaggle GPU 00:00 / 30 hrs` under Settings. A new draft notebook, [Hung 39 Development verification T4](https://www.kaggle.com/code/hungluongduc/hung-39-development-verification-t4/edit), was created. Its settings showed `GPU T4 x2` selected and Internet on. **No GPU process/device probe ran**, so allocation remains unconfirmed.
- Kaggle's [Notebook documentation](https://www.kaggle.com/docs/notebooks) describes a 12-hour GPU session and up to 20 GB of persisted `/kaggle/working` output. The local verification artifact was 73,069,805 bytes across 163 files and took 19 minutes 51 seconds on a different GPU. Neither measurement guarantees Kaggle time, network access, or output retention until a version completes and its files are checked.
- The Kaggle editor remained on `Loading Editor…`; `File > Import Notebook` and cell execution were disabled. Reloading did not resolve it. The draft has a title and GPU setting only. No code, input archive, checkpoint, or forecast was uploaded to or produced by this notebook.

## Prepared implementation

- `experiments/hung_sprint2/kaggle_39_verification.ipynb` is a thin runner. It clones the public repository from `codex/39-completion`, checks out exact code commit `f52371823c1ddbf765eacfe2b89f7bcc0baf4869`, installs the pinned requirements, requires `torch 2.8.0+cu126` and a real CUDA device, and records the actual GPU name. A CPU runtime fails before data processing.
- It downloads the public DATA-v1 UrbanEV input ZIP, requires 151,254,390 bytes and SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`, runs the existing ZIP verifier, checks extraction paths and uses only the pinned Development inputs. The ZIP is temporary; results go under a unique `/kaggle/working/hung-39-kaggle-verification-20261025-v1` directory.
- It invokes the unchanged `run_development.py` with the v2 selection, v1 diagnostic config, verification phase, CUDA, budgets 7/14/28 and seeds 7/11/19. The driver preserves completed stages on rerun only if code and checkpoint hashes match, and rejects incomplete/conflicting stages instead of overwriting them.
- The final notebook cell requires 63 completed stage manifests, verifies 63 checkpoint and 36 replay-journal hashes, and writes `kaggle_verification_summary.json` with lineage and per-replay coverage/metrics. It does not invent metrics for zero scored days. A notebook version must be saved and downloaded/output hashes independently checked before it becomes durable handoff evidence.
- Locally, the five notebook cells parsed and all code cells compiled. The hash-checking logic was tested read-only against the completed local verification folder: 63 stages and 99 matching hashes. This checks the notebook's verifier fields, **not** Kaggle execution, GPU compatibility, download reachability or full matrix completion.

## Evidence required before final reporting

1. Import the notebook once Kaggle's editor works; check the accelerator again and execute the pinned CUDA probe. Record `nvidia-smi`, PyTorch CUDA result, code commit, ZIP/manifest hashes and unique run ID. Stop if GPU or archive verification fails.
2. Run the entire predeclared verification matrix, save a notebook version, and independently recheck all persisted manifests, checkpoint/journal hashes, event ordering, coverage, elapsed time, peak allocation and artifact size. Keep adaptation and `source_checkpoint_only` separate; leave MAE/RMSE undefined where no complete labels arrive.
3. Seek team acceptance of Kaggle as the replacement training platform. Representative-set execution, implementation comparison with Quyền, independent PR review and integration remain separate gates for #39. Kaggle verification alone does not close #39 or complete #22.

No prior Colab/local output was modified or deleted. No Final/test data was used for configuration selection.
