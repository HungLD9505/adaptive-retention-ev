# Hùng Development legacy cost split audit — 29 October 2026

## Result

No authenticated candidate/audit cost split was recovered for the **161 legacy single-policy runs**. The split remains **null for 161/161** in the [Development CPU audit v2](hung-development-audit-20261028-v2/report.md). The recorded total runtime counters and final-stage duration remain usable at their stated scope. Neither `audit_calls: 0` nor the absence of a decision list establishes a measured zero audit cost or a partition of inference/update time.

| Method | Runs examined | Split recovered |
| --- | ---: | ---: |
| `target_only` | 69 | 0 |
| `frozen_source` | 69 | 0 |
| `seasonal_naive` | 23 | 0 |
| **Total** | **161** | **0** |

## Source inventory and checks

The exact 161 job IDs were selected by method from the [v5 Development ledger](hung-development-782-job-ledger-20261028-v5.csv), which points to 11 repository-local ZIP archives. For **every** selected job, this audit read the `replay-42` and `replay-90` run manifests, dispatch measurements and stage receipts, plus the job receipt, `replay-90` log, forecast journal and runner checkpoint. ZIP member reads checked CRC. All 161 `replay-90` manifest byte hashes matched the ledger's stage hash. All 161 final runner checkpoint hashes and all 161 forecast journal hashes matched their respective `replay-90` manifest fields. The full switch audit already binds those archives and manifests to the 782-job Development set; this pass did not rehash entire ZIP archives.

The 322 stage manifests have one aggregate `cost` object per stage with exactly `audit_calls`, `candidate_count`, `fallback_hours`, `inference_calls`, `inference_ns`, `update_ns` and `update_steps`. None contains a candidate/audit cost partition. The 322 dispatch measurements contain only wall time, local hash readback time, output byte count and scope. The 322 stage receipts and 161 job receipts bind files/stages but add no split counter. The 161 logs and forecast journals contain no candidate/audit cost fields. A non-executing `pickletools` string-key inspection of all 161 `replay-90/runner.pt` checkpoints likewise found only aggregate cost keys, with no `candidate`/`audit` partition or per-part inference/update counters. No checkpoint was unpickled or executed.

The aggregate `candidate_count: 1` and `audit_calls: 0` describe the single-policy runner; they are not an observed split of `inference_calls`, `inference_ns`, `update_steps` or `update_ns`. Assigning all aggregate calls to candidate and zero to audit would introduce an inference that the saved schema does not authenticate. The existing null values should therefore remain unchanged. If this split is required for a future cost comparison, it needs a separately instrumented, prospectively locked run; it cannot be recovered from these saved Development bytes.

**Scope:** repository-local Development evidence only. No provider call, new training, Final/test access, changed metric, or archive mutation.
