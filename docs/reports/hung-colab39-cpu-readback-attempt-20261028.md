# #39 owned Colab CPU Drive readback — 28 October 2026

**Outcome:** the [owned notebook](https://colab.research.google.com/drive/1XqqAX-sAdxYEhtcUARgiIuDfffxN8pPb#scrollTo=7RvFYCegmPJj) ran a new read-only CPU cell successfully after the user completed Google's Drive authorization. This was a fresh runtime readback of existing Drive files, independent of the original saved T4 execution. It did not rerun training or modify the original run folder. The [36-row numeric export](hung-colab39-36-replay-metrics-20261028.csv) transcribes the printed replay manifests, including the scored-zero cells and per-row manifest/checkpoint SHA-256.

The notebook's appended cell `cell-7RvFYCegmPJj` mounted `MyDrive/hung-sprint2-runs/hung-39-verification-20261025T024400Z`, checked run identity, read and SHA-256 hashed every file in its 163-file map, checked all 63 stage checkpoint SHA-256 values against stage manifests, and printed the 36 replay manifest rows. A second read-only cell, `cell-JKw3qcfGr3xh`, exported the exact [163-row file map](hung-colab39-163-file-map-20261028.csv) from that runtime after asserting its canonical digest. The original seven cells and [saved T4 proof](hung-colab39-saved-notebook-proof-20261028.md) remain unchanged. Neither appended cell contains a training or Drive-write command.

## Direct cell output

| Check | Observed value |
| --- | --- |
| Run ID | `hung-39-verification-20261025T024400Z` |
| Stage manifests | `source=9`, `target=18`, `replay=36`; total `63` |
| Drive files read | `163` |
| Bytes read | `72,529,254` |
| Run identity SHA-256 | `8a603e4034f2231708cb1d7c930fde92a8f2b7132d4931e4b372a871e2fb260f` |
| Canonical file-map SHA-256 | `fff712cc0d6c683b2ba9c7524c244e365afbdf2c7dcfba88a8b76662eabb28f1` |
| Versioned file-map CSV SHA-256 | `b3e59701a2f52d22b69d7f5b1b04b9903dbec19ffbc41b2367b83bb63b372ca9` |
| Replay rows | `36` |
| Canonical replay-row JSON SHA-256 | `89d8be2af33466a97cf4b6f75b69407d1d54cf8e455d7811ff873cd75e336353` |
| Versioned CSV SHA-256 | `1654f5366596bcd5dd693e8a2db669de3eac6a8bd299db046819197140a5418e` |

The cell's `SUMMARY` was printed after all assertions; it exited without a traceback. The canonical row digest is over `json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False)` in the notebook, and the file-map digest uses the same canonical form for the list of file path, byte count and SHA-256 entries. The CSV is a human-readable projection of those 36 printed rows, not the exact canonical JSON byte stream.

Local CSV validation found 36 unique replay paths, 22 fields per row, and 64-hex-character manifest and checkpoint hashes for every row. `18` rows have numeric live MAE/RMSE and `18` have `scored=0` with null live metrics; these null cells are retained, not imputed. The requested replay counts are `42` for 18 rows and `90` for 18 rows. Scored counts are `0` for 18 rows, `41` for 9, `52` for 6 and `90` for 3. These are Colab #39 verification-run results; they must not be silently merged into the separate 782-job Kaggle Development matrix or used to tune Final from test labels.

## Access history and limits

The first CPU execution stopped at `drive.mount('/content/drive')` with `ValueError: mount failed` before any file read. The user then clicked Google's **Continue** step for this notebook. A single retry mounted `/content/drive`, completed all checks, and printed `SUMMARY` plus 36 `ROW` records. The browser later briefly showed a Colab JavaScript-load error. After dismissing it, the notebook again rendered the saved read-only cells and 163 file-map rows. A reviewer can inspect those outputs or rerun only the read-only cells if a fresh display is required; **do not use Run all**, because original cell 4 invokes Development training.

This is independent **runtime** readback from Drive bytes, not an external download/restore of the 72.5 MB folder. The complete per-file map is now committed as a 163-row repository artifact with path, byte count and SHA-256. Local validation reconstructed the canonical JSON in row order and matched `fff712cc0d6c683b2ba9c7524c244e365afbdf2c7dcfba88a8b76662eabb28f1`; it also matched the CSV SHA-256 above. All 36 replay manifest/checkpoint SHA pairs in the numeric CSV match their paths in the file map. The notebook showed **All changes saved**, and both read-only cells plus the 163-row output remained visible after dismissing a transient JavaScript-load error. Colab #39 scientific acceptance still needs a non-author reviewer to assess protocol coverage and the null scored cells. No Final gate is implied by this readback.

**Checks run:** live Colab CPU cell and output inspection; local Python CSV parse/count/uniqueness/hash-format checks for both CSVs, 163-row byte sum and canonical digest reconstruction; repository link check and `git diff --check`. No model tests or training were run for this documentation/export change.
