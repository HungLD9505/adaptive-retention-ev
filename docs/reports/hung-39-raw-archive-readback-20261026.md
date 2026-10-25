# #39 Kaggle raw archive readback — 2026-10-26

## Scope

Verify the byte-preserving private Kaggle copy of the completed local representative Development ZIP. This was a CPU integrity check only; it did not rerun training, alter the frozen selection/configuration, or use Final/test data. The earlier upload attempt and processing state are recorded in [the upload report](hung-39-raw-archive-upload-20261026.md).

## Executed cloud evidence

- Dataset: [Hung 39 representative archive bytes 20261026, private Version 1](https://www.kaggle.com/datasets/hungluongduc/hung-39-representative-archive-bytes-20261026). Kaggle lists two files: `hung-39-representative-local-20261025T2103.zip.bin` and `archive-integrity.json`.
- Notebook: [Hung 39 Development verification T4, saved Version 5](https://www.kaggle.com/code/hungluongduc/hung-39-development-verification-t4?scriptVersionId=362225233), Quick Save named `CPU raw archive SHA CRC readback`. Kaggle shows a successful 9.8-second run. Only the added raw archive readback cell ran in this version; the original setup/training cells did not execute. Version 1 remains the T4 training verification.
- The cell located exactly one `.bin` under `/kaggle/input`, asserted the private dataset mount path and sidecar, streamed SHA-256 over all bytes, then used `zipfile.testzip()` for full ZIP member CRC readback.
- Saved output: `Kaggle raw archive bytes 249622687 sha256 7d74ec06f9102d1a7357da380bc252570cab2a817a9fcce48030f89c3311f2fa`; `ZIP members 573 uncompressed bytes 287115600 CRC PASS`; `Kaggle raw archive readback PASS`.
- The CPU draft session was stopped after saving. The Version 5 viewer was reloaded and displayed the executed output independently of that session.

The cloud raw archive's size and SHA-256 equal the original local ZIP's recorded size and SHA-256. Assuming SHA-256 collision resistance, the archived bytes match. The earlier [mounted extracted-file readback](hung-39-cloud-mounted-readback-20261026.md) separately matched all 573 file paths, lengths and content hashes after removing Kaggle's one mount prefix.

## Remaining limit

At the last UI check, the dataset-level `kagglehub` and ZIP download controls still said `awaiting compression`. No downloaded dataset ZIP or local re-download SHA/CRC check is claimed. A separate download destination confined to this repository has not been available through the supported Chrome UI. This is a retrieval-interface check, distinct from the completed cloud raw-byte integrity check. Colab/Drive verification and peer acceptance retain their separate status in the Phase E handoff.

The source archive, old dataset, checkpoints, prior reports and notebook versions were preserved. No Codex usage reset was used.
