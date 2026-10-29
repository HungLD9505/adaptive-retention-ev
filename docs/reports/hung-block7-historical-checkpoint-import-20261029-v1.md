# Block7 historical checkpoint import inventory — 29 October 2026

**Status:** request prepared; historical files remain absent. This is a file-byte recovery gate, not a payload-equivalence or scientific-acceptance result. It neither changes the 69 historical run identities nor launches replay/training.

The [create-only 78-file request CSV](hung-block7-historical-checkpoint-request-20261029-v1.csv) is derived from the [69-cell pair table](hung-block7-manifest-pairs-20261028.csv), whose SHA-256 is `e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de`. The request CSV SHA-256 is `4518230acfff6a1adba73f4a0733b7289155e306dcc6d8922a6217bafcf82cd1`. It maps each **9 unique Source** and **69 unique Target** historical checkpoint SHA to one exact staging filename under the current repository's ignored `.cache/block7-historical-import-v1/`, with budget/seed and historical run IDs. Shared Source files appear once. The original path strings remain in the pinned ignored coverage copy; this inventory does not access those paths or any file outside the current repository.

The [read-only byte gate](../../tools/hung_block7_historical_import.py) rechecks the pair-table SHA, exact 69 historical IDs and 9/69 unique file counts. It then hashes staged file bytes and reports `VERIFIED`, `MISSING`, `MISMATCH` and unexpected filenames. It rejects a staging directory that resolves outside the repository, and never follows a symlinked staged checkpoint. The first actual check returned **0/78 verified, 78 missing, 0 mismatch, no unexpected entry**; the command exits 1 until every expected file is present and correct. The prior [repository-wide availability audit](hung-block7-payload-availability-20261028.md) also found 0/9 Source and 0/69 Target exact historical hashes in direct `.pt` files and ZIP members.

After the original checkpoint bytes have been copied create-only to the staged filenames specified in the CSV, run from repository root:

```sh
python -m tools.hung_block7_historical_import
```

If the request CSV must be regenerated, `python -m tools.hung_block7_historical_import --write-request` creates it only when absent or checks it byte-for-byte when present. The command still exits 1 while checkpoint files are missing; that is an evidence status, not a training failure. No credentials or raw checkpoints belong in Git.

A successful 78/78 file-byte gate would only enable the next audit: deserialize the historical and pinned Main Source/Target pairs, compare model/optimizer/latent-scale/RNG payloads and input/causal eligibility with a declared numeric tolerance, then obtain a non-author Block7 decision. File-byte verification alone cannot establish that historical Block7 runs are fair matched comparisons. The prepared 69-replay contingency remains unused unless the reviewer decides equivalence is unsupported.

Focused synthetic tests cover shared-Source deduplication, missing/wrong/extra files, a fully correct staged set, invalid digests and cross-stratum Source reuse. The request was generated and checked without reading files outside this repository.
