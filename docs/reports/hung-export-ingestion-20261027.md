# Deterministic CPU export ingestion — 27 October 2026

Related: #22, #23, #10 and PR #72. This supplements the existing sprint schedule.

`tools/hung_ingest_export.py` removes repeated manual decoding and receipt checks
from the seven prepared CPU export batches. It consumes observed log text through
`--log`/`--log-sha256`, the fixed allocation through
`--manifest`/`--manifest-sha256`, an explicit `--batch`, `--root` and a new `--output`
directory. These are CLI interfaces; no actual80-job batch ingestion is claimed
at this report's creation.

The decoder accepts ordinary DOM table text or native accessibility text with
identical repeated rows. Conflicting duplicates, missing/extra chunks, invalid
base64/zlib streams, concatenated streams, oversized output, wrong byte length
or wrong SHA fail closed. Decompression is bounded to32MiB. The decoded export
must match the exact batch, immutable allocation, expected80 jobs and CPU-only
Development scope. The existing merger recomputes metrics from daily errors and
rejects duplicate logical runs and invalid coverage. A terminal receipt is written
atomically only after these checks. Existing/partial output directories are never
overwritten; failed partial evidence is preserved without a success receipt.

Six offline tests passed for transport duplication/corruption, exact readback,
allocation/job-set mutation and partial-output preservation. The decoder also ran
against the previously completed20-job Kaggle shard8 export:30 chunks,270,418 bytes,
SHA `b7b28cb8c70c75a5268ae94b9026a0ec67d53a5d36f0aa6a51b4e24fefc0035e`.
Decoded bytes exactly matched the earlier independently hash-checked local copy.
This validates real transport decoding, not execution of the new80-job producer.

The new coordinator draft remains prepared while the Chrome tab-control connection
is unavailable. No export batch or GPU execution has been inferred from that draft.
Previously submitted Python training/verification workers continue independently;
their actual handles must be checked before adopting later evidence. No independent
scientific acceptance, Final lock, #39 approval, merge or issue closure is claimed.
