# #39 raw archive upload attempt — 2026-10-26

## Purpose

Test a byte-preserving cloud handoff for the completed representative Development ZIP without changing the original run, the original private Kaggle dataset, or notebook Version 1. This attempt used CPU/browser I/O only; it did not train or inspect Final/test data.

## Local source and upload

- Source: `runs/hung-39-representative-local-20261025T2103.zip`, 249,622,687 bytes, SHA-256 `7d74ec06f9102d1a7357da380bc252570cab2a817a9fcce48030f89c3311f2fa`.
- An ignored staging path under `.cache/cloudbytes-20261026/` hardlinks that ZIP as `hung-39-representative-local-20261025T2103.zip.bin`; local size and SHA-256 were checked before upload. The `.bin` suffix was intended to retain the ZIP as one raw file, avoiding Kaggle's automatic ZIP extraction.
- The existing integrity sidecar was copied as `archive-integrity.json` into the same ignored staging directory.
- Chrome uploaded both files to the new **private** [Kaggle dataset Version 1](https://www.kaggle.com/datasets/hungluongduc/hung-39-representative-archive-bytes-20261026). The Data Card showed exactly two files: the 249.62 MB `.bin` and the 342 B JSON sidecar. This confirms the file listing and upload workflow, not a cloud byte hash.

## Verification status

At the last UI check, Kaggle's dataset download menu still displayed `kagglehub (awaiting compression)` and `Download dataset as zip (awaiting compression)`. The new dataset was not returned by the notebook Add Input search, and a notebook launched from its Code menu remained at `Loading Editor`. Therefore the raw `.bin` has **not** been hashed in Kaggle or downloaded and checked locally. Do not treat the upload listing as a completed byte roundtrip.

The original dataset's 573 extracted files already passed an independent Kaggle mounted-file SHA readback in [the separate report](hung-39-cloud-mounted-readback-20261026.md). That proves the mounted contents of the original archive, but not availability of Kaggle's compressed download.

## Next check

After Kaggle finishes dataset processing, mount the new private dataset in a CPU notebook; stream SHA-256 over the raw `.bin`, check its exact 249,622,687-byte size and ZIP CRC/member inventory, and save the executed notebook version. If a browser download can be directed into a new path inside this repository, verify its raw SHA-256 and CRC locally. Keep both original and new Kaggle datasets private, and preserve all existing run artifacts.
