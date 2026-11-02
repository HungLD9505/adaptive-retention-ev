# Block7/Main 69-cell manifest comparison — 28 October 2026

This [69-row review table](hung-block7-manifest-pairs-20261028.csv) supplements the [Block7 fairness audit](hung-block7-fairness-20261027-v1.md). It is **not** a peer decision or a matched-run relabel. All historical Block7 IDs retain their original identity and `PENDING_PEER` status.

The read-only [generator](../../tools/hung_block7_manifest_pairs.py) rehashed a copy of the original 121,893-byte coverage JSON (SHA-256 `52e39a8330c929aa44cc1df21fdbc257a0ad74bfadddb4e3aa3b0da04697631a`) against the fingerprint in the tracked coverage audit. The 69 historical Block7 and 69 Main run manifests were copied from their earlier project worktrees into this worktree's ignored `.cache/block7-review-v1/manifests/`; the generator reopened only these local copies and rehashed each against its recorded SHA-256. The CSV records both manifest and Source/Target file SHA identities per cell, budget and seed.

| Manifest-level check | Passing pairs |
| --- | ---: |
| Input binding after isolating Source checkpoint file SHA lineage | 69/69 |
| Source input binding | 69/69 |
| Replay config except `controller.block_days` | 69/69 |
| Executed source-file hash map | 69/69 |
| Issued/scored coverage counts | 69/69 |
| Historical manifest Source/Target SHA matches its original coverage record | 69/69 |
| Historical block length 7; Main block length 14 | 69/69 |

The historical Source and Target checkpoint **file** SHAs differ from Main in all 9 Source strata and 69 Target cells, as earlier audits reported. The manifest check deliberately isolates the Source file SHA from input binding and does not imply those files are equal. PR #70 previously reported model/optimizer/scale/RNG payload equality in 9/9 Source and 69/69 Target pairs; this table does **not** rehash or deserialize those paired checkpoint payloads. It also does not establish equal per-origin forecast or label eligibility, numeric tolerance, training schedule semantics, or reviewer acceptance. A reviewer must check the prior payload proof and these remaining protocol conditions before accepting historical equivalence. Otherwise, the 69 new replay IDs described in the fairness audit remain required.

Reproduce with `python -X utf8 -m tools.hung_block7_manifest_pairs` when the ignored copied coverage and 138 manifests are present. The tool compares an existing CSV byte-for-byte and will not overwrite it. The command exited 0: 69 rows, 69 manifest-consistent, zero manifest mismatch, **zero peer accepted**. No training or Final evaluation was run.

An in-memory negative check changed one recorded manifest SHA and `compare` rejected it with `ValueError: Missing or changed manifest`. `git diff --check` passed. The repository suite and Ruff checks are recorded against the clean commit in the PR handoff.
