# Hùng Final — 360-job verification and artifact ledger v1

This create-only handoff joins the immutable 360-job Final jobset, the separate Kaggle CPU archive readback, and the CPU checkpoint-recomputed score rows. It adds [one row per locked job](jobs.csv) and preserves the [full remote job→artifact path map](remote-job-artifact-map.json) byte-for-byte. It does not retrain, relabel, or enlarge the frozen three-station Final.

| Source | SHA-256 / bound identity |
| --- | --- |
| Final lock | `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`; execution code `929480bfb123aaecab2cb9178f0e9088fb4d6593` |
| Locked 360-job set | `7d09583446d9437cec63956f1673c6d1927428ff80ba59a8a876b9391a7c68a2` |
| [Kaggle producer saved version `/1`](https://www.kaggle.com/code/hungluongduc/hung-final-e5e8fe1c-360-20261029-v1) | Run `363367272`; archive 2,404,391,526 bytes, SHA-256 `531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114`, CRC32 `6a29f6e1` |
| [Separate CPU readback](../hung-final-direct-kaggle-readback-20261029-v1.md) | Receipt SHA-256 `19936edd017e76254abd9481fd8b8637cbf2081df798bee56f15f1cc6b869b8f`; full artifact map SHA-256 `0dca10975d5431ac199909ccb5bf69298040d6e4a21d3424bd15986a26cfa0a8` |
| [Separate CPU metrics](../hung-final-analysis-20261029-v1/README.md) | Receipt SHA-256 `657264b1330d48b77f65ea032e3a69f351c6ba8f657a3ae432a3e1060b23bc65`; score source SHA-256 `9e09ae4f72b13c03ed029deb338301753ae377c15cbbfa7414433c5538cba73a` |
| Published [360-row CSV](jobs.csv) | SHA-256 `45ea49c707c3bd608936934f0273704a710050beefa0b06bff5528d8cd312454`; machine summary in [summary.json](summary.json) |

The join found **360/360 unique exact job IDs**, 711 stage maps (360 replay, 324 target initialization, 27 drift reference), 360 scored jobs, zero null/failed jobs, 32,280 scored days and 120 unscored issued origins. Each row records cohort, budget, seed, method, input/source/lock identities, replay manifest and checkpoint paths/SHA, provider version, coverage, metric status and failure reason. The saved CPU metrics program loaded all terminal replay checkpoints to recompute the score rows. Its verification and the readback receipt are the basis for the per-row statuses.

`remote_archive_bytes_sha_crc_verified=TRUE` means the **separate Kaggle CPU saved version** streamed and verified the producer archive and members. `local_archive_bytes_verified=FALSE` is deliberate: the 2.4 GB archive itself was not downloaded to drive D. The small receipt, map and score source were downloaded and hashed locally. The full map lists every remote artifact path, but these rows do not expose each member's byte count/hash separately; the verifier checked those members inside Kaggle. `replay_manifest_sha256` and `replay_checkpoint_sha256` are the hashes reported by the checkpoint-recomputing CPU run. The per-job execution configuration is bound by the pinned global lock/jobset and each replay manifest; this table does not assert a separately published per-job config-file hash.

Reproduce with the exact saved small outputs in the ignored repository `.cache` (the CLI refuses an existing output directory):

```powershell
python -m tools.hung_final_verification_ledger_v1 --output-dir docs/reports/hung-final-verification-ledger-20261029-v2
python -m unittest discover -s tests -p test_hung_final_verification_ledger_v1.py -v
```

The [generator](../../../tools/hung_final_verification_ledger_v1.py) pins all local input hashes, requires the terminal remote readback receipt, reuses the independent Final score/jobset validator, rejects malformed stage/checkpoint maps, and writes create-only output. `summary.json` carries the exact CSV digest. This is technical artifact and metric verification for the **bounded** Final, not independent scientific acceptance of Block7, parity, CHARGED or Colab #39, and not evidence for the 370 omitted UrbanEV IDs or six CHARGED city scopes.
