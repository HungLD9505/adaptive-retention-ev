# Colab #39 Drive artifact identity and peer-access check — 29 October 2026

The owner opened the exact existing run folder in Google Drive without downloading or modifying its contents:

- Folder: [`MyDrive/hung-sprint2-runs/hung-39-verification-20261025T024400Z`](https://drive.google.com/drive/u/0/folders/19PO7AtTQjnC1EWD6uP64Tq_ecgpHU-s7).
- The visible top level contains `7d/`, `14d/`, `28d/` and `matrix_identity.json`. The folder name and URL were observed in the Drive browser address and breadcrumb; this is a direct identity, not a guessed search result.
- The Drive sharing dialog listed only the owner under **People with access** and **Restricted** under general access. It said only people with access can open the link. Therefore this URL is **not yet peer-accessible**, and an author session cannot establish a non-author readback.

The prior [owner CPU readback](hung-colab39-cpu-readback-attempt-20261028.md) reports 163 files / 72,529,254 bytes, 63 checkpoint hashes and 36 replay rows. Its [file map](hung-colab39-163-file-map-20261028.csv) and [metrics rows](hung-colab39-36-replay-metrics-20261028.csv) are tracked for review. This folder inspection did not rehash those files, rerun Colab cells or upgrade the scientific acceptance status. The 18 null-scored replay rows remain null.

**Required handoff:** the owner must grant the assigned non-author reviewer read access to this exact folder through an approved Drive sharing action, or provide an equivalently controlled peer-accessible immutable copy. The reviewer must then independently read and hash the bytes against the tracked file map, inspect the 63 stage/checkpoint bindings and 36 rows, and record an explicit disposition on #39/PR #72. No sharing permission was changed during this check.

**Checks:** read-only Chrome Drive folder and sharing-dialog inspection; no local tests or data transfer were needed for this access-state observation.
