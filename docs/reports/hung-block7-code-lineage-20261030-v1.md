# Historical Block7/Main execution-code lineage assessment

The [machine audit](hung-block7-code-lineage-20261030-v1.json) reopens the **69 exact-SHA paired replay-90 manifests** named in the [pair table](hung-block7-manifest-pairs-20261028.csv). Every historical manifest records Git commit `a0edded8228e8a1b64b0aee18c2655d94a1c4144`; every Main manifest records `969f3deca111e998b197fedd869e891c753a4417`. The tool reads the 11 recorded executed source files directly from each Git commit and hashes their raw bytes. All **22 commit/file hashes** equal the manifest values, and each of the 69 paired source-hash maps is identical.

The complete Git tree diff between these two **actual replay commits**, with rename detection disabled, contains exactly one deletion: `docs/reports/hung-integrated-development-20261026.md`. There is no changed or added executable file in that commit comparison. The 69 manifest pairs also record identical Python `3.13.7`, PyTorch `2.8.0+cu126`, CUDA runtime `12.6` and NVIDIA GeForce RTX 3050 Ti Laptop GPU identities; variable peak-memory telemetry is not treated as method configuration. After removing `controller.block_days`, the saved replay configs are equal in all 69 pairs; historical Block7 uses 7 days and Main uses 14 days. Both replay manifests were recorded with clean execution worktrees.

This closes the **code-commit difference** as a reason by itself to reject the historical comparison. The distinct commit IDs reflect a documentation deletion, not a change to the recorded executable method. The distinct Source/Target checkpoint **file** hashes remain real: the [payload audit](hung-block7-payload-comparison-20261029-v1.md) establishes equal model/optimizer/scale/RNG state in 9/9 Source and 69/69 Target pairs while preserving their different metadata and Source-hash lineage. The [full trace audit](hung-block7-full-trace-audit-20261030-v2.md) authenticates the 90-day event and label schedule and records policy-dependent forecast differences rather than treating them as failed parity.

**Research assessment for the assigned non-author reviewer:** Under the existing block-size ablation contract, these results support treating the 69 historical Block7 runs as comparable physical runs for the 7-versus-14-day policy contrast. A 69-job replay is not justified solely by the distinct Git commit IDs or checkpoint file hashes. The reviewer must still record `ACCEPTED_EQUIVALENT` or `REPLAY_REQUIRED` with any additional exact objection, such as a required fresh-run identity or a specific unverified execution dependency. This author-side assessment is **not** the peer disposition, does not relabel historical jobs as newly executed, and does not approve Hùng–Qyroven head/bootstrap parity or the bounded Final's wider scope.

Reproduce from the repository root while the ignored, SHA-pinned manifest copies remain available:

```sh
python -m tools.hung_block7_code_lineage_v1 --output docs/reports/hung-block7-code-lineage-20261030-v2.json
python -m unittest tests.test_hung_block7_code_lineage_v1 -v
```

The command writes create-only; use a fresh output path and compare bytes with the published JSON. It does not read Final labels, retrain or modify an earlier artifact.
