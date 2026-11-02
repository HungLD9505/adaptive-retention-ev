# Colab #39 independent byte readback handoff — 29 October 2026

The exact [Colab #39 Drive folder](https://drive.google.com/drive/u/0/folders/19PO7AtTQjnC1EWD6uP64Tq_ecgpHU-s7) is shared with the assigned reviewer as Editor, with general access Restricted ([access checkpoint](hung-colab39-drive-access-20261029-v2.md)). This handoff supplies a **read-only** verifier for the reviewer to run from their own authorized account after mounting or downloading that exact folder. It does not itself constitute non-author readback or scientific acceptance.

From the repository root, with the exact folder available locally to the reviewer:

```powershell
python -m tools.hung_colab39_peer_readback --folder "<path to hung-39-verification-20261025T024400Z>"
```

The verifier pins the committed [163-file map](hung-colab39-163-file-map-20261028.csv) to SHA-256 `b3e59701a2f52d22b69d7f5b1b04b9903dbec19ffbc41b2367b83bb63b372ca9`, checks the exact file set (including missing/extra files), reads every expected file, and checks each byte count and SHA-256. A pass prints `status: VERIFIED`, `verified_files: 163`, and `verified_bytes: 72529254` in JSON and exits 0; any mismatch prints `FAILED` with paths and exits 1. The reviewer should preserve their command output and execution environment as a peer-owned artifact on #39 / PR #72, then inspect the 63 stage/checkpoint bindings and 36 replay rows, including the 18 null-scored rows, against the [owner readback](hung-colab39-cpu-readback-attempt-20261028.md). **Do not run all cells** of the original notebook: one original cell invokes training.

The tool has no Drive API, no training call, and no output file write. Its tests cover the pinned map and changed, missing, and extra bytes; they do not replace running it on the reviewer-accessible folder. The folder contents were not accessed from a reviewer account in preparing this handoff.
