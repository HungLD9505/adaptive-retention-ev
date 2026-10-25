# #39 Kaggle mounted artifact readback — 2026-10-26

## Objective and scope

Verify that the private Kaggle dataset retains the 573 files from the completed local representative Development archive. This is a CPU integrity check. It does not rerun training, change the frozen matrix, use Final/test data, or establish model effectiveness.

## Local reference

The existing archive is `runs/hung-39-representative-local-20261025T2103.zip`, 249,622,687 bytes, SHA-256 `7d74ec06f9102d1a7357da380bc252570cab2a817a9fcce48030f89c3311f2fa`. Its 573 file members total 287,115,600 uncompressed bytes. For each member, the readback computed the archive member name, byte length, and SHA-256. It sorted those records by name, serialized them as compact UTF-8 JSON (`ensure_ascii=False`, separators `(',', ':')`), then hashed the serialization. The local tree SHA-256 was `14edf23fc253ef33fa22e30f95937250f75e7cb317c01a73d69ccd420530746c`.

## Kaggle execution and result

- Dataset: [private representative archive, Version 1](https://www.kaggle.com/datasets/hungluongduc/hung-39-representative-local-20261025t2103).
- Saved notebook evidence: [Version 4, CPU mounted archive hash readback](https://www.kaggle.com/code/hungluongduc/hung-39-development-verification-t4?scriptVersionId=362216281). Kaggle shows a successful 9.6-second Quick Version. Its four original setup/training cells were not executed in this version; only the final readback cell ran. The earlier T4 training verification remains Version 1.
- The notebook attached the private dataset with accelerator `None` and read the mounted files under `/kaggle/input/datasets/hungluongduc/hung-39-representative-local-20261025t2103/`.
- The mounted dataset adds one outer `hung-39-representative-local-20261025T2103/` directory before the archive member paths. The first attempt compared paths without removing that mount prefix and failed the tree assertion despite matching file count and total bytes. The corrected cell removes exactly that one prefix and asserts its expected name.
- Corrected output: `files 573 bytes 287115600 tree_sha256 14edf23fc253ef33fa22e30f95937250f75e7cb317c01a73d69ccd420530746c`, followed by `Kaggle mounted-file readback PASS`. The sidecar's archived ZIP SHA-256 also matched the local reference.

This proves byte-for-byte equality of all 573 mounted file contents and their normalized paths against the local ZIP members, assuming SHA-256 collision resistance. The successful notebook output is visible in the saved Version 4 viewer, so it does not depend on the interactive CPU session; that session was stopped after saving.

## Limits and remaining work

Kaggle's dataset download menu still showed `awaiting compression`, and its Code tab showed `Data not available. This dataset may need its archive recreated.` A compressed dataset download and a second local download/CRC roundtrip were therefore not performed. The mounted-file readback is stronger evidence for cloud file contents than the earlier sidecar alone, but it does not prove Kaggle's dataset ZIP download is available or byte-identical to the original archive. Python 3.12 clean notebook execution, Colab tensor/Drive handoff, independent comparison, method/config approval, and peer acceptance retain their separate status in the Phase E report and PR #46.

No existing archive, checkpoint, run, report, or notebook Version 1 was overwritten. No Codex usage reset was used.
