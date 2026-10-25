# #39 platform readiness and durable artifact handoff — 2026-10-25

## Objective and scope

Read the signed-in Chrome Kaggle/Colab UI after the local representative matrix finished. This check verifies displayed quota, saved notebook metadata, and private storage of the local run. It does not launch another training matrix, accept a research configuration, or close #39.

## Kaggle quota and saved verification

At approximately 23:17 ICT, the Kaggle account menu displayed **GPU 27h 34m available of 30h**. This verifies the current quota display; it does not prove that a new GPU runtime would be allocated or that a model tensor used CUDA.

The existing private notebook [Hung 39 Development verification T4](https://www.kaggle.com/code/hungluongduc/hung-39-development-verification-t4) visibly showed **Version 1 of 3**, runtime **24m 16s · GPU T4 x2**, **343 output files**, and logs **1455.9 second run — successful**. These are saved-version UI observations. Artifact/hash validation of that earlier run remains documented separately in `hung-39-kaggle-verification-20261025.md`.

## Colab allocation and bounded probe limitation

Opened the existing configured notebook in Colab and clicked **Connect T4**, without running its historical cells. A transient message stated that the reCAPTCHA service could not be reached. A later observation explicitly showed **Connected to Python 3 Google Compute Engine backend (GPU)** and **T4 (Python 3)**, RAM 0.97/12.67 GB. This is UI-level allocation evidence only.

Opened **File → Open in playground mode**; the banner explicitly stated **Changes will not be saved**. Added one new disposable cell containing only the following device probe:

```python
import json, platform
from pathlib import Path
import torch

probe = {
    "scope": "bounded device probe only; no training",
    "python": platform.python_version(),
    "torch": torch.__version__,
    "cuda_available": torch.cuda.is_available(),
    "drive_already_mounted": Path("/content/drive/MyDrive").is_dir(),
}
if probe["cuda_available"]:
    x = torch.ones(8, device="cuda")
    probe.update(
        device_name=torch.cuda.get_device_name(0),
        tensor_device=str(x.device),
        tensor_sum=float(x.sum().item()),
        cuda_runtime=torch.version.cuda,
    )
print(json.dumps(probe, sort_keys=True))
```

The cell **did not execute**: Colab reported **Too many sessions**. Manage sessions then displayed **Runtime disconnected**, with **Terminate other sessions** disabled, and the reCAPTCHA-service message remained. No other sessions were terminated. No training, dependency install, Drive mount/OAuth, checkpoint save, or model/tensor CUDA result was obtained. Historical notebook contents were preserved through playground mode. Actual Colab tensor/device and fresh Drive checkpoint handoff remain **unverified**, with this connection/session blocker recorded separately from the earlier usage-limit blocker.

## Private representative archive storage

Created a **new Private** Kaggle dataset, without updating existing datasets:

[Hung 39 representative local 20261025T2103](https://www.kaggle.com/datasets/hungluongduc/hung-39-representative-local-20261025t2103)

The UI showed the success notification **Your dataset was created successfully**, creation timestamp **2026-10-25 23:24:40 ICT**, **Private**, and **Version 1**. The supported file-chooser flow uploaded these exact local files:

- `runs/hung-39-representative-local-20261025T2103.zip` — 249,622,687 bytes, SHA-256 `7d74ec06f9102d1a7357da380bc252570cab2a817a9fcce48030f89c3311f2fa`.
- `runs/hung-39-representative-local-20261025T2103-archive-integrity.json` — 342 bytes; its displayed SHA, CRC PASS and member-SHA PASS fields matched the local sidecar supplied by the parent audit.

Kaggle automatically unpacked the ZIP. Data Explorer showed **574 files**, **287.12 MB**: 573 run members plus the integrity sidecar. The original ZIP is therefore represented by its extracted members on Kaggle. A downloaded Kaggle-generated dataset ZIP would have a different outer SHA; compare every member against the local archive rather than expecting the container bytes to match. The inspected Download menu said **Download dataset as zip (awaiting compression)**. Cloud download/readback has not been verified. The supported browser download API exposes a resulting path but no explicit destination; no download into the default location outside the repository was attempted. A future official authenticated CLI download can target a new directory inside the repository.

## Actions and validation status

The browser actions were: inspect existing Kaggle account quota → Your Work → saved verification notebook; open Colab configured notebook → Connect T4 → playground-only probe → inspect session blocker; Kaggle Create → Dataset → choose archive and sidecar → confirm default Private → Create → verify success, version and file inventory. The disposable playground tab was closed. No account/security settings, credentials, quota purchases, Codex reset, public sharing, or duplicate matrix execution were performed.

This report adds one new Markdown file only. Platform evidence is intentionally bounded to the observations above; local execution/audit, notebook clean-environment validation and technical completion gates are recorded by their respective phase reports.
