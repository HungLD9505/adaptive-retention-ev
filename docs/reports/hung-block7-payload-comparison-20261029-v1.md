# Block7 historical checkpoint payload comparison — 29 October 2026

**Result:** 78/78 historical checkpoint files (9 Source, 69 Target; 31,370,508 bytes) were imported create-only into ignored repository staging after exact SHA-256 checks against the pinned [request list](hung-block7-historical-checkpoint-request-20261029-v1.csv). This supersedes the earlier 0/78 availability checkpoint; it does not alter any historical or Main run.

The [deterministic 78-row comparison](evidence/hung-block7-payload-comparison-20261029-v1.json) (SHA-256 `80b8c754a80b127d7d11a96a8776d58dd7fa5406c5e4d63fd848d374c51db009`) rehashes each historical and current Main `.pt` file, loads checkpoint dictionaries with `torch.load(weights_only=True)` on CPU, and compares model, optimizer, latent scale, RNG, configuration and other state recursively. The pinned [69-cell pair table](hung-block7-manifest-pairs-20261028.csv) has SHA-256 `e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de`.

| Pair class | Result | Differences |
| --- | ---: | --- |
| Source, one per budget/seed | 9/9 state-equal | Top-level `code_sha` only. |
| Target, one per historical Main run | 69/69 state-equal | Top-level `code_sha` and `input_binding`; the latter differs only in `source_checkpoint_sha256`, and each value equals its exact historical/Main Source checkpoint hash. |

The comparison rejects any changed state tensor, optimizer field, unexpected key or mismatched Source binding. It verifies checkpoint payload equivalence for the listed pairs. It **does not** establish equality of every per-origin journal byte, numeric replay trajectory, or scientific eligibility for treating 69 historical Main anchors as fresh paired Development runs. The [origin schedule audit](hung-block7-origin-eligibility-20261028.md) checks 69/69 manifest event schedules, with its stated limits. A non-author reviewer still must decide whether this evidence suffices or a separately locked 69-run replay is needed. No replay was launched.

Reproduce from repository root while the ignored historical `.pt` staging and pinned Main payload remain available:

```sh
python -m tools.hung_block7_historical_import
python -m tools.hung_block7_payload_compare_v1
python -m unittest tests.test_hung_block7_payload_compare_v1 -v
```

The tool checks existing evidence byte-for-byte rather than overwriting it. Raw `.pt` files remain outside Git; the tracked JSON contains per-pair immutable hashes and comparison results, not private model weights.
